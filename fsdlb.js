/*
打开微信，进入逢三得利吧小程序，点击右下角“我的”，
打开抓包软件抓取https://xiaodian.miyatech.com 请求头的Authorization 
抓取到的Authorization值即为token，去掉前面的"bearer "，将剩余部分作为token使用。
在面板「环境变量」中添加变量：fsdlbhbck 多个 token 用 # 隔开，例如 token1#token2#token3
*/

const $ = new Env("逢三得利吧小程序签到");
const axios = require("axios");
const defaultUserAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.31(0x18001e31) NetType/WIFI Language/zh_CN miniProgram"

// 环境变量名（青龙面板中需添加此变量，多个token用 # 分隔）
const ENV_NAME = "fsdlbhbck";

// 简易日志
function log(msg) {
    console.log(`[${new Date().toLocaleString()}] ${msg}`);
}

// 全局账号索引
let userIdx = 0;

class Task {
    constructor(token) {
        this.index = userIdx++;
        // 存储纯净 token（不含 bearer）
        this.token = "bearer " + token.trim();
    }

    async run() {
        await this.info();
        await this.signIn();
    }

    async signIn() {
        let options = {
            method: 'POST',
            url: `https://xiaodian.miyatech.com/api/coupon/auth/signIn`,
            headers: {
                "X-VERSION": "2.1.3",
                "Authorization": `${this.token}`,
                "HH-VERSION": "0.2.8",
                "HH-FROM": "20230130307725",
                "HH-APP": "wxb33ed03c6c715482",
                "HH-CI": "saas-wechat-app",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            },
            data: {
                "miniappId": 159
            }
        };
        let { data: result } = await axios.request(options);
        if (result?.code == 200) {
            log(`🕊账号[${this.index}] 签到成功:[${result.data.integralToastText}]🎉`);
        } else {
            log(`🕊账号[${this.index}] 签到失败:${result.msg}🚫`);
        }
    }

    async info() {
        let options = {
            method: 'GET',
            url: `https://xiaodian.miyatech.com/api/user/auth/member/integral/union/flow/list?pageNo=1&pageSize=10&dataType=SCORE`,
            headers: {
                "X-VERSION": "2.1.3",
                "Authorization": `${this.token}`,
                "HH-VERSION": "0.2.8",
                "HH-FROM": "20230130307725",
                "HH-APP": "wxb33ed03c6c715482",
                "HH-CI": "saas-wechat-app",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            },
        };
        let { data: result } = await axios.request(options);
        if (result?.code == 200) {
            log(`🕊账号[${this.index}] 查询成功:总积分[${result.data.totalScore}]🎉`);
        } else {
            log(`🕊账号[${this.index}] 查询失败:${result.msg}🚫`);
        }
    }
}

async function getNotice() {
    try {
        let options = {
            url: `https://ghproxy.net/https://raw.githubusercontent.com/smallfawn/Note/refs/heads/main/Notice.json`,
            headers: {
                "User-Agent": defaultUserAgent,
            },
            timeout: 3000
        };
        let { data: res } = await axios.request(options);
        log(res);
        return res;
    } catch (e) {}
}

!(async () => {
    await getNotice();

    // 读取青龙环境变量
    const envTokens = process.env[ENV_NAME];
    if (!envTokens) {
        log(`❌ 未找到环境变量 ${ENV_NAME}，请在青龙面板中添加。`);
        return;
    }

    // 按 # 分割多个 token
    const tokens = envTokens.split('#').filter(t => t.trim() !== '');
    if (tokens.length === 0) {
        log(`❌ 环境变量 ${ENV_NAME} 内容为空，请正确填写 token。`);
        return;
    }

    log(`📋 共获取到 ${tokens.length} 个账号`);

    for (let token of tokens) {
        await new Task(token).run();
    }
})()
    .catch((e) => console.error(e));
