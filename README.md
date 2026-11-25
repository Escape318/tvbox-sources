# tvbox-sources

盒子上的正式影视源 + 爬虫的 GitHub 副本。**这份配置可以独立运行，不依赖盒子**。

## 两条导入地址（二选一）

| 用途 | 地址 |
|---|---|
| 默认（GitHub 原生，更新快，5 分钟生效） | `https://raw.githubusercontent.com/Escape318/tvbox-sources/main/tvbox.json` |
| 国内不稳时（jsdelivr 镜像，更新有缓存延迟） | `https://cdn.jsdelivr.net/gh/Escape318/tvbox-sources@main/tvbox-cdn.json` |

两份只差爬虫地址：`tvbox.json` 的 `api` 指 raw，`tvbox-cdn.json` 指 jsdelivr。

## 目录

| 路径 | 内容 |
|---|---|
| `tvbox.json` | 13 站，`api` → raw 爬虫，无 `relay:` |
| `tvbox-cdn.json` | 同上，`api` → jsdelivr 镜像 |
| `spider/cms.py` | 通用 maccms 爬虫，与盒子 `/opt/tvbox/cms.py` 逐字节一致 |
| `spider/jianpian.py` | 荐片爬虫，与盒子 `/opt/tvbox/public/jianpian.py` 逐字节一致 |
| `config/sources-pool.json` | 源池登记表（15 条，含中转站，盒子运行态参考） |

## 独立性实测（2026-11-25）

用盒子以外的机器模拟 FongMi：从 GitHub 拉 py → 编译 → 建 Spider 实例 → 请求采集接口、解析播放页。

| 站 | 首页分类 | 首页卡片 | 详情/播放 |
|---|---|---|---|
| 红牛影视 | 39 | 20 | 线路 hnyun → `hn.bfvvs.com/.../index.m3u8` |
| 360影视 | 45 | 20 | 线路 360zy → `vod1.maowushi.com/.../index.m3u8` |
| 金鹰资源 | 38 | 20 | — |
| 荐片 | 6 | 20 | — |

爬虫走 raw 与 jsdelivr 两种地址都能拉到、能跑。直链是从源站 CDN 直接给的，不经过盒子 `/proxy`。

## 站点（13 站）

荐片、百度云影视、追剧影视、非凡影视、红牛影视、360影视、暴风影视、豪华影视、极速影视、量子影视、无尽资源、光速资源、金鹰资源。

## 已知限制（绕不过去的两点）

1. **追剧影视、百度云影视这两个站直连进不去。** 实测（盒子外网络）`api.zuidapi.com` 超时、`api.apibdzy.com` 返 503。这两站原本靠盒子中转才通，拆成直连后需要设备侧开代理（海外 IP）才能进站。其余 11 站在普通网络下可用。
2. **爬虫的 `RELAY` 常量仍写死盒子地址。** 直连模式用不到它；只要不写 `relay:` 前缀就不会碰到。哪天要用回中转，必须把常量改成你实际的中转地址（仓库本身不能当中转服务器）。

## 盒子那边

`/opt/tvbox/public/vod.json` 未改动，仍是 15 站含 6 个中转；`sources-pool.json` 也是盒子运行态。这份仓库只供「盒子不在也能看」的备份用途。
