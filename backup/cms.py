#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 maccms(CMS) 爬虫 + 分享页取流（FongMi Python 版）

适用：api 形如 https://xxx/api.php/provide/vod/ 的站点。
ext 直接填该 API 地址。

两类播放值自动处理：
1) 已是 .m3u8/.mp4 直链 → 原样返回
2) 是 HTML 分享页 → 取页面里的 m3u8/mp4，补成绝对地址（ffzy 这类源常用）
"""

import json
import re
import time
from urllib.parse import quote, urljoin

RELAY = ("https://d109b1527b501d490a54fe05-77e19b9ef7015d05a0d04c18-"
         "http-8080.vivid-hawk-9fb-fi.computers.hoody.com/proxy")

UA = ("Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
DIRECT_RE = re.compile(r"\.(m3u8|mp4|flv)(\?|$)", re.I)
PAGE_URL_RE = re.compile(r"""["'](https?://[^"'<> ]+\.(?:m3u8|mp4|flv)(?:\?[^"'<> ]*)?)["']""", re.I)
REL_URL_RE = re.compile(r"""["'](/(?:[^"'<> ]+)\.(?:m3u8|mp4|flv)(?:\?[^"'<> ]*)?)["']""", re.I)

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def page(self, items, pg, limit, total=None):
            total = total if total else len(items)
            return {"page": int(pg), "pagecount": max(1, int(total / limit) + (1 if total % limit else 0)),
                    "limit": limit, "total": total, "list": items}


class Spider(BaseSpider):
    def init(self, extend=""):
        raw = (extend or "").strip()
        self.relay = ""
        # ext 写成 relay:<接口地址> 时，接口请求经服务器中转（采集站按出口 IP 拦的情况用这个）
        if raw.startswith("relay:"):
            self.relay = RELAY
            raw = raw[6:].strip()
        self.base = raw
        if self.base and not self.base.startswith("http"):
            self.base = "https://" + self.base
        self.origin = ""
        m = re.match(r"(https?://[^/]+)", self.base)
        if m:
            self.origin = m.group(1)

    # ---------------- 请求 ----------------
    def _get(self, params, timeout=15000, retries=3):
        qs = "&".join("%s=%s" % (k, quote(str(v), safe="")) for k, v in params.items()
                       if v not in (None, ""))
        url = self.base + ("&" if "?" in self.base else "?") + qs
        if self.relay:
            url = self.relay + "?u=" + quote(url, safe="")
        # 这类免费接口普遍加了抗压，偶发 503/超时，重试两次再报错
        last = None
        for i in range(max(1, int(retries))):
            try:
                res = self.net.req(url, {"method": "GET", "headers": {"User-Agent": UA},
                                         "timeout": timeout})
            except Exception as exc:
                last = exc
                continue
            code = int(res.get("code") or 0)
            if code == 200:
                raw = res.get("content")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "ignore")
                try:
                    return json.loads(raw)
                except ValueError:
                    raise RuntimeError("接口返回不是 JSON")
            last = RuntimeError("接口 HTTP %s" % code)
            if i < retries - 1:
                try:
                    import time
                    time.sleep(0.8)
                except Exception:
                    pass
        raise last or RuntimeError("接口请求失败")

    @staticmethod
    def _card(v):
        return {
            "vod_id": str(v.get("vod_id")),
            "vod_name": v.get("vod_name") or "",
            "vod_pic": v.get("vod_pic") or "",
            "vod_remarks": v.get("vod_remarks") or "",
            "vod_year": str(v.get("vod_year") or ""),
            "vod_area": v.get("vod_area") or "",
            "type_name": v.get("type_name") or "",
        }

    @staticmethod
    def _page(items, pg, limit, total=None):
        try:
            pg = max(1, int(pg))
        except (TypeError, ValueError):
            pg = 1
        try:
            total = int(total) if total else len(items)
        except (TypeError, ValueError):
            total = len(items)
        return {"page": pg, "pagecount": max(1, (total + limit - 1) // limit),
                "limit": limit, "total": total, "list": items}

    # ---------------- 首页 ----------------
    HOME_TTL = 600

    def _home_key(self):
        host = re.sub(r"https?://", "", self.base).split("/")[0]
        return "cms_home_" + re.sub(r"[^0-9a-zA-Z]", "_", host)

    def _home_cache_get(self):
        try:
            blob = json.loads(self.local.get(self._home_key()) or "{}")
            if (time.time() - float(blob.get("t") or 0)) < self.HOME_TTL and blob.get("d"):
                return blob["d"]
        except Exception:
            pass
        return None

    def _home_cache_set(self, data):
        try:
            self.local.set(self._home_key(), json.dumps({"t": int(time.time()), "d": data},
                                                        ensure_ascii=False))
        except Exception:
            pass

    def homeContent(self, filter):
        cached = self._home_cache_get()
        if cached:
            return cached
        data = self._get({"ac": "list"})
        raw = [c for c in (data.get("class") or []) if c.get("type_id") is not None]
        # 父分类没有直属内容（t=父ID 返回 0 条），只保留叶子分类。
        # 有的接口不给 type_pid，这时按 maccms 惯例丢掉 id<=5 的顶层分类。
        pids = {c.get("type_pid") for c in raw if c.get("type_pid")}
        if pids:
            leaf = [c for c in raw if c.get("type_id") not in pids]
        else:
            leaf = [c for c in raw
                    if not (len(raw) > 8 and str(c.get("type_id")).isdigit()
                            and int(c.get("type_id")) <= 5)]
        classes = [{"type_id": str(c.get("type_id")), "type_name": c.get("type_name")}
                   for c in (leaf or raw)]
        # ac=list 不带封面图，补一次 ac=detail；这类接口常常很慢，只给 6 秒、一次机会，
        # 拿不到就用 list 直接出内容，别把首页卡死
        videos = []
        try:
            d2 = self._get({"ac": "detail", "pg": 1}, timeout=6000, retries=1)
            videos = d2.get("list") or []
        except Exception:
            videos = []
        if not videos:
            videos = data.get("list") or []
        out = {"class": classes, "list": [self._card(v) for v in videos[:30]]}
        if any((v.get("vod_pic") or "").startswith("http") for v in out["list"]):
            self._home_cache_set(out)
        return out

    # ---------------- 分类 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        params = {"ac": "detail", "t": tid, "pg": pg}
        for k, v in (extend or {}).items():
            if v not in (None, "", "全部"):
                params[k] = v
        data = self._get(params)
        items = [self._card(v) for v in (data.get("list") or [])]
        total = data.get("total")
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = None
        return self._page(items, pg, 20, total)

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        data = self._get({"ac": "detail", "wd": key, "pg": pg})
        items = [self._card(v) for v in (data.get("list") or [])]
        return self._page(items, pg, 20, len(items))

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        out = []
        for vid in ids:
            data = self._get({"ac": "detail", "ids": vid})
            rows = data.get("list") or []
            if not rows:
                continue
            v = rows[0]
            play_from = v.get("vod_play_from") or "默认"
            play_url = v.get("vod_play_url") or ""
            item = self._card(v)
            item.update({
                "vod_id": str(v.get("vod_id")),
                "vod_content": re.sub(r"<[^>]+>", "", v.get("vod_content") or "").strip(),
                "vod_director": v.get("vod_director") or "",
                "vod_actor": v.get("vod_actor") or "",
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            })
            out.append(item)
        return {"list": out}

    # ---------------- 播放 ----------------
    # 分享页可能按出口 IP 拦（数据中心 IP 常见 403），换同结构域名再试
    SHARE_HOSTS = ("super.ffzy-online6.com", "vip.ffzy-play8.com", "vip.ffzy-play.com")

    def _share_page(self, page_url):
        target = page_url
        if self.relay:
            target = self.relay + "?u=" + quote(page_url, safe="")
        res = self.net.req(target, {"method": "GET", "headers": {
            "User-Agent": UA,
            "Referer": page_url.split("/", 3)[0] + "//" + page_url.split("/", 3)[2] + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }, "timeout": 15000})
        raw = res.get("content") or ""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "ignore")
        if int(res.get("code") or 0) == 200 and raw:
            return raw, page_url
        try:
            sp = page_url.split("//", 1)[1]
            host, path = sp.split("/", 1)
            path = "/" + path
        except Exception:
            return "", page_url
        for alt in self.SHARE_HOSTS:
            if alt == host:
                continue
            u = "https://" + alt + path
            if self.relay:
                u = self.relay + "?u=" + quote(u, safe="")
            try:
                r = self.net.req(u, {"headers": {"User-Agent": UA, "Referer": "https://" + alt + "/"},
                                     "method": "GET", "timeout": 15000})
                c = r.get("content") or ""
                if isinstance(c, bytes):
                    c = c.decode("utf-8", "ignore")
                if int(r.get("code") or 0) == 200 and "m3u8" in c:
                    return c, u
            except Exception:
                continue
        return "", page_url

    def playerContent(self, flag, pid, vipFlags):
        url = (pid or "").strip()
        if not url:
            return {"parse": 0, "url": "", "msg": "无播放值"}
        if DIRECT_RE.search(url):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA}}
        page_url = url if url.startswith("http") else urljoin(self.origin + "/", url)
        # 分享页形如 .../play/<hash> 时，同目录 /index.m3u8 通常就是直链（豪华、极速这类）
        if re.search(r"/play/[A-Za-z0-9]+/?$", page_url):
            cand = page_url.rstrip("/") + "/index.m3u8"
            res = self.net.req(cand, {"method": "GET", "headers": {"User-Agent": UA}, "timeout": 15000})
            body = res.get("content") or ""
            if isinstance(body, bytes):
                body = body.decode("utf-8", "ignore")
            if int(res.get("code") or 0) == 200 and "#EXTM3U" in body[:200]:
                return {"parse": 0, "url": cand, "format": "application/x-mpegURL",
                        "header": {"User-Agent": UA, "Referer": page_url}}
        raw, page_url = self._share_page(page_url)
        for regex in (PAGE_URL_RE, REL_URL_RE):
            found = regex.findall(raw or "")
            if found:
                target = found[0]
                if not target.startswith("http"):
                    target = urljoin(page_url, target)
                return {"parse": 0, "url": target,
                        "format": "application/x-mpegURL",
                        "header": {"User-Agent": UA, "Referer": page_url}}
        if not raw:
            return {"parse": 0, "url": "", "msg": "分享页被拒绝(403/网络不通)，换线路或换源"}
        return {"parse": 0, "url": "", "msg": "分享页里没找到直链"}
