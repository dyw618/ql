/**
 * cron 8 12 * * *  miaoyouHome.js
 * https://www.popcentury.cn/scrm-rz-minip-tzlm
 * Show:微信公众号 庙友之家 每日签到 积分可换首饰
 * 变量名:miaoyouHome
 * 变量值:JSESSIONID的值
 * 多账号@或换行
 * scriptVersionNow = "0.0.3";
 */
const { Env } = require("./tools/env")
const $ = new Env("庙友之家小程序");
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
