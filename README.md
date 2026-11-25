# tvbox-sources

盒子上的正式影视源 + 爬虫，GitHub 备份。站点配置那份是**中转已改直连**的版本。

## 目录

| 路径 | 内容 |
|---|---|
| `tvbox.json` | 站配置，13 站，无 `relay:`，可直接导进 FongMi |
| `spider/cms.py` | 通用 maccms 爬虫，与盒子 `/opt/tvbox/cms.py` 逐字节一致 |
| `spider/jianpian.py` | 荐片爬虫，与盒子 `/opt/tvbox/public/jianpian.py` 逐字节一致 |
| `config/sources-pool.json` | 源池登记表（15 条，含中转站，是盒子的运行态） |

## 导入地址

```
https://raw.githubusercontent.com/Escape318/tvbox-sources/main/tvbox.json
```

## 站点（13 站）

荐片、百度云影视、追剧影视、非凡影视、红牛影视、360影视、暴风影视、豪华影视、极速影视、量子影视、无尽资源、光速资源、金鹰资源。

## 说明

- 中转站（追剧、百度云、暴风、豪华、极速、量子）已拆 `relay:` 前缀改直连；追剧、百度云拆完后与已有直连站完全重复，已去重，所以 15 → 13。
- `tvbox.json` 里的 `api` 仍指向盒子 `/cms.py`、`/jianpian.py`（盒子在线才能拉到爬虫）。若盒子挂了想继续用，把 `api` 换成仓库 raw 地址：
  - 荐片 → `https://raw.githubusercontent.com/Escape318/tvbox-sources/main/spider/jianpian.py`
  - 其余 12 站 → `https://raw.githubusercontent.com/Escape318/tvbox-sources/main/spider/cms.py`
- 爬虫里的 `RELAY` 常量写死了盒子中转地址，换服务器或换域名必须同步改（目前直连模式用不到它）。
- 盒子上的 `/opt/tvbox/public/vod.json` 未被改动，仍是 15 站含 6 个中转。
