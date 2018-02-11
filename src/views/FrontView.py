# -*- coding: utf-8 -*-
"""
    passport.views.FrontView
    ~~~~~~~~~~~~~~

    The blueprint for front view.

    :copyright: (c) 2017 by staugur.
    :license: MIT, see LICENSE for more details.
"""

from config import VAPTCHA
from utils.web import login_required, anonymous_required, adminlogin_required, dfr, set_sessionId, oauth2_name2type, get_redirect_url, verify_sessionId, analysis_sessionId
from utils.tool import logger, email_check, phone_check
from libs.auth import Authentication
from vaptchasdk import vaptcha as VaptchaApi
from flask import Blueprint, request, render_template, g, redirect, url_for, flash, make_response, jsonify, abort


#初始化前台蓝图
FrontBlueprint = Blueprint("front", __name__)
#初始化手势验证码服务
vaptcha = VaptchaApi(VAPTCHA["vid"], VAPTCHA["key"])

@FrontBlueprint.route('/')
def index():
    #首页
    return render_template("index.html")

@FrontBlueprint.route("/test")
def test():
    return "test"

@FrontBlueprint.route('/user/')
@login_required
def userhome():
    #貌似不需要
    return render_template("index.html")

@FrontBlueprint.route('/user/setting/')
@login_required
def userset():
    """用户基本设置"""
    return render_template("user/set.html")

@FrontBlueprint.route('/user/app/')
@adminlogin_required
def userapp():
    Action = request.args.get("Action")
    if Action == "editView":
        # 编辑应用
        return render_template("user/apps.edit.html")
    # 默认返回应用选项卡
    return render_template("user/apps.html")

@FrontBlueprint.route('/signUp', methods=['GET', 'POST'])
@anonymous_required
def signUp():
    if request.method == 'POST':
        sceneid = request.args.get("sceneid") or "02"
        token = request.form.get("token")
        challenge = request.form.get("challenge")
        if token and challenge and vaptcha.validate(challenge, token, sceneid):
            account = request.form.get("account")
            vcode = request.form.get("vcode")
            password = request.form.get("password")
            repassword = request.form.get("repassword")
            register_ip = request.headers.get('X-Real-Ip', request.remote_addr)
            auth = Authentication(g.mysql, g.redis)
            try:
                res = auth.signUp(account=account, vcode=vcode, password=password, repassword=repassword, register_ip=register_ip)
            except Exception,e:
                logger.error(e, exc_info=True)
                flash(u"系统异常，请稍后再试")
            else:
                res = dfr(res)
                if res["success"]:
                    # 写登陆日志
                    return redirect(url_for('.signIn'))
                else:
                    flash(res["msg"])
        else:
            flash(u"人机验证失败")
        return redirect(url_for('.signUp'))
    return render_template("auth/signUp.html")

@FrontBlueprint.route('/signIn', methods=['GET', 'POST'])
def signIn():
    """ 单点登录、注销
    登录流程
        1. Client跳转到Server的/sso/页面，携带参数sso(所需sso信息的加密串)。
        2. 校验参数通过后，Server跳转到/signIn/页面，设置ReturnUrl(从数据库读取)，且不携带参数；校验未通过不携带参数直接返回错误信息。
        3. 用户在Server未登录时，输入用户名密码或第三方登录成功后，创建全局会话(设置Server登录态)、授权令牌(ticket)，根据ticket生成sid(登录态id)写入redis，并携带ticket返回ReturnUrl；
           已登录时，创建ticket并携带跳回ReturnUrl。
        4. Client用ticket到Server校验(通过api方式)，通过redis校验cookie是否存在
        -- sso加密规则：
            aes_cbc("app_name:app_id.app_secret")
        -- sso校验流程：
            根据sso参数，验证是否有效，解析参数获取name、id、secret等，并用name获取到对应信息一一校验
        -- 备注：
            第3步，需要signIn、OAuthGuide方面路由设置
            第4步，需要在插件内增加api路由
    注销流程
    """
    if request.method == 'POST':
        sceneid = request.args.get("sceneid") or "01"
        token = request.form.get("token")
        challenge = request.form.get("challenge")
        if token and challenge and vaptcha.validate(challenge, token, sceneid):
            account = request.form.get("account")
            password = request.form.get("password")
            login_ip = request.headers.get('X-Real-Ip', request.remote_addr)
            auth = Authentication(g.mysql, g.redis)
            res = auth.signIn(account=account, password=password)
            res = dfr(res)
            if res["success"]:
                # 记录登录日志
                auth.brush_loginlog(res, login_ip=login_ip, user_agent=request.headers.get("User-Agent"))
                # 登录成功，设置cookie
                sessionId = set_sessionId(uid=res["uid"])
                response = make_response(redirect(g.redirect_uri))
                # 设置cookie根据浏览器周期过期，当无https时去除`secure=True`
                secure = False if request.url_root.split("://")[0] == "http" else True
                response.set_cookie(key="sessionId", value=sessionId, max_age=None, httponly=True, secure=secure)
                return response
            else:
                flash(res["msg"])
        else:
            flash(u"人机验证失败")
        return redirect(url_for('.signIn'))
    else:
        sso = request.args.get("sso")
        sso_isOk = False
        sso_returnUrl = None
        if verify_sessionId(sso):
            # sso jwt payload
            sso = analysis_sessionId(sso)
            if sso and isinstance(sso, dict) and "app_name" in sso and "app_id" in sso and "app_secret" in sso:
                # 通过app_name获取注册信息并校验参数
                app_data = g.api.userapp.getUserApp(sso["app_name"])
                if app_data:
                    if sso["app_id"] == app_data["app_id"] and sso["app_secret"] == app_data["app_secret"]:
                        sso_isOk = True
                        sso_returnUrl = app_data["app_redirect_url"] + "?Action=login"
                        #return redirect(url_for("front.signIn", ReturnUrl=sso_returnUrl))
        logger.debug("sso_isOk: {}, ReturnUrl: {}".format(sso_isOk, sso_returnUrl))
        if sso_isOk:
            return render_template("auth/signIn.html", ReturnUrl=sso_returnUrl)
        else:
            return render_template("auth/signIn.html", ReturnUrl=g.redirect_uri)

@FrontBlueprint.route("/OAuthGuide")
@anonymous_required
def OAuthGuide():
    """OAuth2登录未注册时引导路由，选择绑定已有账号或直接登录(首选)"""
    if request.args.get("openid"):
        return render_template("auth/OAuthGuide.html")
    else:
        return redirect(g.redirect_uri)

@FrontBlueprint.route("/OAuthGuide/DirectLogin", methods=["POST"])
@anonymous_required
def OAuthDirectLogin():
    """OAuth2直接登录(首选)"""
    if request.method == 'POST':
        openid = request.form.get("openid")
        if openid:
            auth = Authentication(g.mysql, g.redis)
            # 直接注册新账号并设置登录态
            ip = request.headers.get('X-Real-Ip', request.remote_addr)
            res = auth.oauth2_signUp(openid, ip)
            res = dfr(res)
            if res["success"]:
                # 记录登录日志
                auth.brush_loginlog(res, login_ip=ip, user_agent=request.headers.get("User-Agent"))
                # 登录成功，设置cookie
                sessionId = set_sessionId(uid=res["uid"])
                response = make_response(redirect(get_redirect_url("front.userset")))
                # 设置cookie根据浏览器周期过期，当无https时去除`secure=True`
                secure = False if request.url_root.split("://")[0] == "http" else True
                response.set_cookie(key="sessionId", value=sessionId, max_age=None, httponly=True, secure=secure)
                return response
            else:
                flash(res["msg"])
                return redirect(url_for("front.OAuthGuide", openid=openid))
        else:
            return redirect(g.redirect_uri)

@FrontBlueprint.route("/OAuthGuide/BindAccount", methods=["GET", "POST"])
@anonymous_required
def OAuthBindAccount():
    """OAuth2绑定已有账号登录"""
    if request.method == 'POST':
        openid = request.form.get("openid")
        sceneid = request.args.get("sceneid") or "03"
        token = request.form.get("token")
        challenge = request.form.get("challenge")
        if token and challenge and vaptcha.validate(challenge, token, sceneid):
            account = request.form.get("account")
            password = request.form.get("password")
            auth = Authentication(g.mysql, g.redis)
            res = auth.oauth2_bindLogin(openid=openid, account=account, password=password)
            res = dfr(res)
            if res["success"]:
                # 记录登录日志
                auth.brush_loginlog(res, login_ip=request.headers.get('X-Real-Ip', request.remote_addr), user_agent=request.headers.get("User-Agent"))
                # 登录成功，设置cookie
                sessionId = set_sessionId(uid=res["uid"])
                response = make_response(redirect(get_redirect_url("front.userset", _anchor="bind")))
                # 设置cookie根据浏览器周期过期，当无https时去除`secure=True`
                secure = False if request.url_root.split("://")[0] == "http" else True
                response.set_cookie(key="sessionId", value=sessionId, max_age=None, httponly=True, secure=secure)
                return response
            else:
                flash(res["msg"])
        else:
            flash(u"人机验证失败")
        return redirect(url_for('.OAuthBindAccount', openid=openid))
    else:
        openid = request.args.get("openid")
        if openid:
            return render_template("auth/OAuthBindAccount.html")
        else:
            return redirect(g.redirect_uri)

@FrontBlueprint.route("/logout")
@login_required
def logout():
    response = make_response(redirect(get_redirect_url('.signIn')))
    response.set_cookie(key='sessionId', value='', expires=0)
    return response

@FrontBlueprint.route("/unbind")
@login_required
def unbind():
    identity_name = request.args.get("identity_name")
    if identity_name:
        auth = Authentication(g.mysql, g.redis)
        identity_type = oauth2_name2type(identity_name)
        res = auth.unbind(g.uid, identity_type)
        res = dfr(res)
        if res["code"] == 0:
            flash(u"解绑成功")
        else:
            flash(res["msg"])
    else:
        flash(u"无效参数")
    return redirect(url_for("front.userset", _anchor="bind"))