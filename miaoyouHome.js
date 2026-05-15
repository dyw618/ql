/**
 * cron 8 12 * * *  miaoyouHome.js
 * https://www.popcentury.cn/scrm-rz-minip-tzlm
 * Show:微信公众号 庙友之家 每日签到 积分可换首饰
 * 变量名:miaoyouHome
 * 变量值:JSESSIONID的值
 * 多账号@或换行 
 * scriptVersionNow = "0.0.3";
 */

const $ = new Env("庙友之家小程序");
const notify = $.isNode() ? require('../sendNotify') : '';
let ckName = "miaoyouHome";
let envSplitor = ["@", "\n"];
let strSplitor = "&";
let userIdx = 0;
let userList = [];

const SCENE_GAME_INSTANCE_CODE = "xOc8YsVkScdD";

class UserInfo {
    constructor(str) {
        this.index = ++userIdx;
        let cookieStr = str.split(strSplitor)[0];
        if (cookieStr && !cookieStr.includes('JSESSIONID=')) {
            cookieStr = 'JSESSIONID=' + cookieStr;
        }
        this.ck = cookieStr;
        this.ckStatus = true;
        this.pointsBalance = 0;
        this.signStatus = false;
        this.signMessage = "";
        this.useChance = 0;
        this.chance = 0;
    }
    
    async main() {
        await this.initData();
        if (!this.signStatus && this.ckStatus) {
            await this.task();
            await this.initData(); // 签到后重新查询积分
        }
    }
    
    async initData() {
        try {
            let options = {
                fn: "查询数据",
                method: "post",
                url: `https://www.popcentury.cn/scrm-rz-minip-tzlm/minipPointsController/initInstanceMemberAwards`,
                params: {
                    sceneGameInstanceCode: SCENE_GAME_INSTANCE_CODE
                },
                headers: {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Host": "www.popcentury.cn",
                    "Referer": "https://servicewechat.com/wx10b22bd20e2bccca/14/page-frame.html",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254160e) XWEB/18163",
                    "x-requested-with": "XMLHttpRequest",
                    "xweb_xhr": "1",
                    "Cookie": this.ck
                },
                body: "{}"
            }
            
            let { body: result } = await $.httpRequest(options);
            
            if (result && result.code == 200) {
                if (result.data) {
                    this.useChance = result.data.useChance || 0;
                    this.chance = result.data.chance || 0;
                    // 如果已签到，useChance 应该是 0 或已使用
                    this.signStatus = (this.useChance === 0 && this.chance === 0) ? true : false;
                    $.log(`[账号${this.index}] ✅ 查询成功 | 剩余抽奖次数: ${this.chance} | 已使用: ${this.useChance}`);
                } else {
                    $.log(`[账号${this.index}] ✅ 查询成功: ${JSON.stringify(result)}`);
                }
            } else {
                $.log(`[账号${this.index}] ❌ 查询失败: ${result?.message || JSON.stringify(result)}`);
                if (result?.code == 599) {
                    this.ckStatus = false;
                }
            }
        } catch (e) {
            $.log(`[账号${this.index}] ❌ 请求异常: ${e.message}`);
        }
    }
    
    async task() {
        if (this.signStatus) {
            $.log(`[账号${this.index}] ⏭️ 今日已签到，跳过`);
            return;
        }
        
        try {
            let options = {
                fn: "签到",
                method: "post",
                url: `https://www.popcentury.cn/scrm-rz-minip-tzlm/minipPointsController/extractInstanceMemberAwards`,
                params: {
                    sceneGameInstanceCode: SCENE_GAME_INSTANCE_CODE
                },
                headers: {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Host": "www.popcentury.cn",
                    "Referer": "https://servicewechat.com/wx10b22bd20e2bccca/14/page-frame.html",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254160e) XWEB/18163",
                    "x-requested-with": "XMLHttpRequest",
                    "xweb_xhr": "1",
                    "Cookie": this.ck
                },
                body: "{}"
            }
            
            let { body: result } = await $.httpRequest(options);
            
            if (result && result.code == 200) {
                let awardMsg = result.data?.awardPoints ? `+${result.data.awardPoints}积分` : '成功';
                this.signMessage = `✅ 签到${awardMsg}`;
                $.log(`[账号${this.index}] ${this.signMessage}`);
                this.signStatus = true;
            } else {
                this.signMessage = `❌ 签到失败: ${result?.message || '未知错误'}`;
                $.log(`[账号${this.index}] ${this.signMessage}`);
            }
        } catch (e) {
            $.log(`[账号${this.index}] ❌ 签到异常: ${e.message}`);
            this.signMessage = `签到异常: ${e.message}`;
        }
    }
    
    getSummary() {
        return `账号${this.index}: ${this.signMessage || (this.signStatus ? '已签到' : '未签到')}`;
    }
}

async function start() {
    for (let user of userList) {
        if (user.ckStatus) {
            await user.main();
        }
    }
    
    let summary = [];
    for (let user of userList) {
        summary.push(user.getSummary());
    }
    if (summary.length > 0) {
        $.log("\n========== 签到汇总 ==========");
        summary.forEach(s => $.log(s));
    }
}

!(async () => {
    if (!(await checkEnv())) return;
    if (userList.length > 0) {
        await start();
    }
    await $.SendMsg($.logs.join("\n"));
})()
.catch((e) => console.log(e))
.finally(() => $.done());

async function checkEnv() {
    let userCookie = ($.isNode() ? process.env[ckName] : $.getdata(ckName)) || "";
    if (userCookie) {
        let e = envSplitor[0];
        for (let o of envSplitor) {
            if (userCookie.indexOf(o) > -1) {
                e = o;
                break;
            }
        }
        for (let n of userCookie.split(e)) {
            if (n && n.trim()) {
                userList.push(new UserInfo(n.trim()));
            }
        }
    } else {
        console.log("未找到CK，请设置环境变量 " + ckName);
        return false;
    }
    console.log(`共找到${userList.length}个账号`);
    return true;
}

/////////////////////////////////////////////////////////////////////////////////////
function Env(t, s) {
    return new (class {
        constructor(t, s) {
            this.name = t;
            this.data = null;
            this.dataFile = "box.dat";
            this.logs = [];
            this.logSeparator = "\n";
            this.startTime = new Date().getTime();
            Object.assign(this, s);
            this.log("", `\ud83d\udd14${this.name}, \u5f00\u59cb!`);
        }
        isNode() {
            return "undefined" != typeof module && !!module.exports;
        }
        isQuanX() {
            return "undefined" != typeof $task;
        }
        isSurge() {
            return "undefined" != typeof $httpClient && "undefined" == typeof $loon;
        }
        isLoon() {
            return "undefined" != typeof $loon;
        }
        getScript(t) {
            return new Promise((s) => {
                this.get({ url: t }, (t, e, i) => s(i));
            });
        }
        runScript(t, s) {
            return new Promise((e) => {
                let i = this.getdata("@chavy_boxjs_userCfgs.httpapi");
                i = i ? i.replace(/\n/g, "").trim() : i;
                let o = this.getdata("@chavy_boxjs_userCfgs.httpapi_timeout");
                (o = o ? 1 * o : 20), (o = s && s.timeout ? s.timeout : o);
                const [h, a] = i.split("@"),
                    r = {
                        url: `http://${a}/v1/scripting/evaluate`,
                        body: { script_text: t, mock_type: "cron", timeout: o },
                        headers: { "X-Key": h, Accept: "*/*" },
                    };
                this.post(r, (t, s, i) => e(i));
            }).catch((t) => this.logErr(t));
        }
        loaddata() {
            if (!this.isNode()) return {};
            {
                this.fs = this.fs ? this.fs : require("fs");
                this.path = this.path ? this.path : require("path");
                const t = this.path.resolve(this.dataFile),
                    s = this.path.resolve(process.cwd(), this.dataFile),
                    e = this.fs.existsSync(t),
                    i = !e && this.fs.existsSync(s);
                if (!e && !i) return {};
                {
                    const i = e ? t : s;
                    try {
                        return JSON.parse(this.fs.readFileSync(i));
                    } catch (t) {
                        return {};
                    }
                }
            }
        }
        writedata() {
            if (this.isNode()) {
                this.fs = this.fs ? this.fs : require("fs");
                this.path = this.path ? this.path : require("path");
                const t = this.path.resolve(this.dataFile),
                    s = this.path.resolve(process.cwd(), this.dataFile),
                    e = this.fs.existsSync(t),
                    i = !e && this.fs.existsSync(s),
                    o = JSON.stringify(this.data);
                e ? this.writeFileSync(t, o) : i ? this.fs.writeFileSync(s, o) : this.fs.writeFileSync(t, o);
            }
        }
        lodash_get(t, s, e) {
            const i = s.replace(/\[(\d+)\]/g, ".$1").split(".");
            let o = t;
            for (const t of i) if (((o = Object(o)[t]), void 0 === o)) return e;
            return o;
        }
        lodash_set(t, s, e) {
            return Object(t) !== t
                ? t
                : (Array.isArray(s) || (s = s.toString().match(/[^.[\]]+/g) || []),
                    (s
                        .slice(0, -1)
                        .reduce(
                            (t, e, i) =>
                                Object(t[e]) === t[e]
                                    ? t[e]
                                    : (t[e] = Math.abs(s[i + 1]) >> 0 == +s[i + 1] ? [] : {}),
                            t
                        )[s[s.length - 1]] = e),
                    t);
        }
        getdata(t) {
            let s = this.getval(t);
            if (/^@/.test(t)) {
                const [, e, i] = /^@(.*?)\.(.*?)$/.exec(t),
                    o = e ? this.getval(e) : "";
                if (o)
                    try {
                        const t = JSON.parse(o);
                        s = t ? this.lodash_get(t, i, "") : s;
                    } catch (t) {
                        s = "";
                    }
            }
            return s;
        }
        setdata(t, s) {
            let e = !1;
            if (/^@/.test(s)) {
                const [, i, o] = /^@(.*?)\.(.*?)$/.exec(s),
                    h = this.getval(i),
                    a = i ? ("null" === h ? null : h || "{}") : "{}";
                try {
                    const s = JSON.parse(a);
                    this.lodash_set(s, o, t), (e = this.setval(JSON.stringify(s), i));
                } catch (s) {
                    const h = {};
                    this.lodash_set(h, o, t), (e = this.setval(JSON.stringify(h), i));
                }
            } else e = this.setval(t, s);
            return e;
        }
        getval(t) {
            if (this.isSurge() || this.isLoon()) {
                return $persistentStore.read(t);
            } else if (this.isQuanX()) {
                return $prefs.valueForKey(t);
            } else if (this.isNode()) {
                this.data = this.loaddata();
                return this.data[t];
            } else {
                return this.data && this.data[t] || null;
            }
        }
        setval(t, s) {
            if (this.isSurge() || this.isLoon()) {
                return $persistentStore.write(t, s);
            } else if (this.isQuanX()) {
                return $prefs.setValueForKey(t, s);
            } else if (this.isNode()) {
                this.data = this.loaddata();
                this.data[s] = t;
                this.writedata();
                return true;
            } else {
                return this.data && this.data[s] || null;
            }
        }
        initGotEnv(t) {
            this.got = this.got ? this.got : require("got");
            this.cktough = this.cktough ? this.cktough : require("tough-cookie");
            this.ckjar = this.ckjar ? this.ckjar : new this.cktough.CookieJar();
            if (t) {
                t.headers = t.headers ? t.headers : {};
                if (typeof t.headers.Cookie === "undefined" && typeof t.cookieJar === "undefined") {
                    t.cookieJar = this.ckjar;
                }
            }
        }
        /**
        * @param {Object} options
        * @returns {String} 将 Object 对象 转换成 queryStr: key=val&name=senku
        */
        queryStr(options) {
            return Object.entries(options)
                .map(([key, value]) => `${key}=${typeof value === 'object' ? JSON.stringify(value) : value}`)
                .join('&');
        }
        isJSONString(str) {
            try {
                var obj = JSON.parse(str);
                if (typeof obj == 'object' && obj) {
                    return true;
                } else {
                    return false;
                }
            } catch (e) {
                return false;
            }
        }
        isJson(obj) {
            var isjson = typeof (obj) == "object" && Object.prototype.toString.call(obj).toLowerCase() == "[object object]" && !obj.length;
            return isjson;
        }
        async SendMsg(message) {
            if (!message) return;
            if ($.isNode()) {
                await notify.sendNotify($.name, message)
            } else {
                $.msg($.name, '', message)
            }
        }
        async httpRequest(options) {
            const t = {
                ...options
            };
            if (!t.headers) {
                t.headers = {}
            }
            if (t.params) {
                t.url += '?' + this.queryStr(t.params);
            }
            t.method = t.method.toLowerCase()
            if (t.method.toLowerCase() === 'get') {
                delete t.headers['Content-Type'];
                delete t.headers['Content-Length'];
                delete t["body"]
            }
            if (t.method.toLowerCase() === 'post') {
                let contentType

                if (!t.body) {
                    t.body = ""
                } else {
                    if (typeof t.body == "string") {
                        if (this.isJSONString(t.body)) {
                            contentType = 'application/json'
                        } else {
                            contentType = 'application/x-www-form-urlencoded'
                        }
                    } else if (this.isJson(t.body)) {
                        t.body = JSON.stringify(t.body)
                        contentType = 'application/json'
                    }
                }
                if (!t.headers['Content-Type']) {
                    t.headers['Content-Type'] = contentType;
                }
                delete t.headers['Content-Length'];
            }
            if (this.isNode()) {
                this.initGotEnv(t);
                let httpResult = await this.got(t)
                if (this.isJSONString(httpResult.body)) {
                    httpResult.body = JSON.parse(httpResult.body)
                }
                return httpResult;
            }
        }
        randomNumber(length) {
            const characters = '0123456789';
            return Array.from({ length }, () => characters[Math.floor(Math.random() * characters.length)]).join('');
        }
        randomString(length) {
            const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
            return Array.from({ length }, () => characters[Math.floor(Math.random() * characters.length)]).join('');
        }
        timeStamp() {
            return new Date().getTime()
        }
        uuid() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
                var r = Math.random() * 16 | 0,
                    v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }
        time(t) {
            let s = {
                "M+": new Date().getMonth() + 1,
                "d+": new Date().getDate(),
                "H+": new Date().getHours(),
                "m+": new Date().getMinutes(),
                "s+": new Date().getSeconds(),
                "q+": Math.floor((new Date().getMonth() + 3) / 3),
                S: new Date().getMilliseconds(),
            };
            /(y+)/.test(t) &&
                (t = t.replace(
                    RegExp.$1,
                    (new Date().getFullYear() + "").substr(4 - RegExp.$1.length)
                ));
            for (let e in s)
                new RegExp("(" + e + ")").test(t) &&
                    (t = t.replace(
                        RegExp.$1,
                        1 == RegExp.$1.length
                            ? s[e]
                            : ("00" + s[e]).substr(("" + s[e]).length)
                    ));
            return t;
        }
        msg(s = t, e = "", i = "", o) {
            const h = (t) =>
                !t || (!this.isLoon() && this.isSurge())
                    ? t
                    : "string" == typeof t
                        ? this.isLoon()
                            ? t
                            : this.isQuanX()
                                ? { "open-url": t }
                                : void 0
                        : "object" == typeof t && (t["open-url"] || t["media-url"])
                            ? this.isLoon()
                                ? t["open-url"]
                                : this.isQuanX()
                                    ? t
                                    : void 0
                            : void 0;
            this.isMute ||
                (this.isSurge() || this.isLoon()
                    ? $notification.post(s, e, i, h(o))
                    : this.isQuanX() && $notify(s, e, i, h(o)));
            let logs = ['', '==============📣系统通知📣=============='];
            logs.push(t);
            e ? logs.push(e) : '';
            i ? logs.push(i) : '';
            console.log(logs.join('\n'));
            this.logs = this.logs.concat(logs);
        }
        log(...t) {
            t.length > 0 && (this.logs = [...this.logs, ...t]),
                console.log(t.join(this.logSeparator));
        }
        logErr(t, s) {
            const e = !this.isSurge() && !this.isQuanX() && !this.isLoon();
            e
                ? this.log("", `\u2757\ufe0f${this.name}, \u9519\u8bef!`, t.stack)
                : this.log("", `\u2757\ufe0f${this.name}, \u9519\u8bef!`, t);
        }
        wait(t) {
            return new Promise((s) => setTimeout(s, t));
        }
        done(t = {}) {
            const s = new Date().getTime(),
                e = (s - this.startTime) / 1e3;
            this.log(
                "",
                `\ud83d\udd14${this.name}, \u7ed3\u675f! \ud83d\udd5b ${e} \u79d2`
            ),
                this.log(),
                (this.isSurge() || this.isQuanX() || this.isLoon()) && $done(t);
        }
    })(t, s);
}
