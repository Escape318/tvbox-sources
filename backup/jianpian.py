#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荐片 H5 API 直连爬虫（FongMi / TVBox Python 版）

链路：/api/v1 + HMAC-SHA256 请求签名 + AES-256-GCM 加密信封（请求体与响应体）
纯标准库实现，不依赖 cryptography / pycryptodome。

id 约定：列表卡片 vod_id = work_id；播放值 = "work_id|episode_index|line_key"
"""

import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import quote

API = "/api/v1/"
DEFAULT_BASE = "https://h5.jianpian.tv"
UA = ("Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
CT_ENVELOPE = "application/vnd.jp.encrypted+json"


# ---------------------------------------------------------------- base64url
def b64u(data):
    if isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
    else:
        raw = data.encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def unb64u(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ------------------------------------------------------------------- AES-GCM
_SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d]


def _xtime(a):
    a <<= 1
    return a ^ 0x11b if a & 0x100 else a


def _expand_key(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        tmp = list(w[i - 1])
        if i % nk == 0:
            tmp = tmp[1:] + tmp[:1]
            tmp = [_SBOX[b] for b in tmp]
            tmp[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            tmp = [_SBOX[b] for b in tmp]
        w.append([w[i - nk][j] ^ tmp[j] for j in range(4)])
    flat = []
    for word in w:
        flat += word
    return flat, nr


def _encrypt_block(rk, nr, block):
    st = bytearray(block)
    for i in range(16):
        st[i] ^= rk[i]
    for rnd in range(1, nr + 1):
        for i in range(16):
            st[i] = _SBOX[st[i]]
        # ShiftRows：第 r 行左移 r 位，行 r 的字节索引是 4*c+r
        st = bytearray([st[0], st[5], st[10], st[15],
                        st[4], st[9], st[14], st[3],
                        st[8], st[13], st[2], st[7],
                        st[12], st[1], st[6], st[11]])
        if rnd != nr:
            for c in range(4):
                a = [st[4 * c], st[4 * c + 1], st[4 * c + 2], st[4 * c + 3]]
                t = a[0] ^ a[1] ^ a[2] ^ a[3]
                st[4 * c] ^= t ^ _xtime(a[0] ^ a[1])
                st[4 * c + 1] ^= t ^ _xtime(a[1] ^ a[2])
                st[4 * c + 2] ^= t ^ _xtime(a[2] ^ a[3])
                st[4 * c + 3] ^= t ^ _xtime(a[3] ^ a[0])
        base = 16 * rnd
        for i in range(16):
            st[i] ^= rk[base + i]
    return bytes(st)


class AESGCM(object):
    def __init__(self, key):
        self.rk, self.nr = _expand_key(key)
        self.h = _encrypt_block(self.rk, self.nr, bytes(16))

    def _ctr(self, nonce, data):
        out = bytearray()
        ctr = 1
        for off in range(0, len(data), 16):
            ctr += 1
            block = nonce + (ctr & 0xffffffff).to_bytes(4, "big")
            ks = _encrypt_block(self.rk, self.nr, block)
            chunk = data[off:off + 16]
            out += bytes(a ^ b for a, b in zip(chunk, ks))
        return bytes(out)

    def _mul_h(self, value):
        v = int.from_bytes(self.h, "big")
        z = int.from_bytes(value, "big")
        res = 0
        for i in range(128):
            if (z >> (127 - i)) & 1:
                res ^= v
            v = (v >> 1) ^ 0xe1000000000000000000000000000000 if v & 1 else v >> 1
        return res.to_bytes(16, "big")

    def _ghash(self, aad, ct):
        y = bytes(16)
        for src in (aad, ct):
            for i in range(0, len(src), 16):
                pad = src[i:i + 16]
                pad += bytes(16 - len(pad))
                y = self._mul_h(bytes(a ^ b for a, b in zip(y, pad)))
        lens = (len(aad) * 8).to_bytes(8, "big") + (len(ct) * 8).to_bytes(8, "big")
        return self._mul_h(bytes(a ^ b for a, b in zip(y, lens)))

    def seal(self, nonce, plaintext, aad=b""):
        ct = self._ctr(nonce, plaintext)
        tag = bytes(a ^ b for a, b in zip(self._ghash(aad, ct),
                                          _encrypt_block(self.rk, self.nr, nonce + b"\x00\x00\x00\x01")))
        return ct + tag

    def open(self, nonce, data, aad=b""):
        ct, tag = data[:-16], data[-16:]
        expect = bytes(a ^ b for a, b in zip(self._ghash(aad, ct),
                                             _encrypt_block(self.rk, self.nr, nonce + b"\x00\x00\x00\x01")))
        if not hmac.compare_digest(tag, expect):
            raise ValueError("aes-gcm: tag mismatch")
        return self._ctr(nonce, ct)


# ------------------------------------------------------------------ spider
try:
    from base.spider import Spider as BaseSpider
except Exception:                                    # 本机调试用占位
    class BaseSpider(object):
        def page(self, items, pg, limit, total=None):
            count = int((total or len(items)) / limit) + 1
            return {"page": int(pg), "pagecount": count, "limit": limit,
                    "total": total or len(items), "list": items}


class Spider(BaseSpider):
    def init(self, extend=""):
        base = (extend or "").strip()
        if base and not base.startswith("http"):
            base = "https://" + base
        self.base = (base or DEFAULT_BASE).rstrip("/")
        self.sess = None
        ident = ""
        cred = ""
        try:
            ident = self.local.get("jp_install") or ""       # 站点隔离存储
            cred = self.local.get("jp_cred") or ""
        except Exception:
            pass
        if len(ident) < 16:
            ident = self._uuid()
        if len(cred) < 20:
            cred = b64u(os.urandom(32))
        self.install_id = ident
        self.credential = cred
        try:
            self.local.set("jp_install", ident)
            self.local.set("jp_cred", cred)
        except Exception:
            pass
        self._keys()

    # ---------------- 密钥派生 ----------------
    def _keys(self):
        ident = ("jp-api-v1\x00" + self.install_id).encode()
        master = hmac.new(hashlib.sha256(ident).digest(), self.credential.encode(), hashlib.sha256).digest()
        self.k_auth = hmac.new(master, b"jp-api-request-auth-v1\x01", hashlib.sha256).digest()
        self.k_req = hmac.new(master, b"jp-api-request-body-v1\x01", hashlib.sha256).digest()
        self.k_resp = hmac.new(master, b"jp-api-response-body-v1\x01", hashlib.sha256).digest()

    @staticmethod
    def _uuid():
        raw = bytearray(os.urandom(16))
        raw[6] = (raw[6] & 0x0f) | 0x40
        raw[8] = (raw[8] & 0x3f) | 0x80
        h = raw.hex()
        return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])

    # ---------------- 请求 ----------------
    def _request(self, method, path, query=None, body=None):
        uri = API + path
        if query:
            qs = "&".join("%s=%s" % (k, quote(str(v), safe="")) for k, v in query.items()
                          if v is not None and str(v) != "")
            if qs:
                uri += "?" + qs
        ts = int(time.time())
        nonce = os.urandom(12)
        headers = {
            "Accept": "application/json, application/problem+json",
            "X-Client-App": "jp",
            "X-Client-Platform": "h5",
            "X-Client-Version": "5.0.45",
            "X-Client-Build": "1",
            "X-Device-ID": self.install_id,
            "Accept-Language": "zh-CN",
            "X-JP-Runtime-Authorization": "Bearer " + self.credential,
            "X-JP-Crypto-Version": "1",
            "X-JP-Accept-Business-Status": "body",
            "X-JP-Timestamp": str(ts),
            "X-JP-Nonce": b64u(nonce),
        }
        payload = ""
        if body is not None:
            plain = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
            aad = ("jp-api-request-v1\n%s\n%s\n%d\n%s\n%s"
                   % (method, uri, ts, b64u(nonce), self.install_id)).encode()
            ct = AESGCM(self.k_req).seal(nonce, plain, aad)
            payload = json.dumps({"v": 1, "alg": "A256GCM", "ts": ts, "data": b64u(ct)})
            headers["Content-Type"] = CT_ENVELOPE
        body_hash = hashlib.sha256(payload.encode() if payload else b"").hexdigest()
        sig = hmac.new(self.k_auth, ("%s\n%s\n%d\n%s\n%s" % (method, uri, ts, b64u(nonce), body_hash)).encode(),
                       hashlib.sha256).digest()
        headers["X-JP-Signature"] = b64u(sig)
        opts = {"method": method, "headers": headers, "timeout": 15000}
        if payload:
            opts["body"] = payload
        res = self.net.req(self.base + uri, opts)
        return self._decode(res, method, uri, ts, nonce)

    def _decode(self, res, method, uri, ts, nonce):
        code = int(res.get("code") or 0)
        raw = res.get("content")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "ignore")
        text = raw or ""
        heads = res.get("headers") or {}
        low = {str(k).lower(): str(v) for k, v in heads.items()}
        enc = low.get("x-jp-crypto-version") == "1" or CT_ENVELOPE in low.get("content-type", "")
        if not enc:
            try:
                data = json.loads(text) if text else {}
            except ValueError:
                data = {}
        else:
            try:
                env = json.loads(text)
                n = unb64u(env["nonce"])
                aad = ("jp-api-response-v1\n%s\n%s\n%d\n%d\n%s\n%s"
                       % (method, uri, code, ts, b64u(nonce), self.install_id)).encode()
                data = json.loads(AESGCM(self.k_resp).open(n, unb64u(env["data"]), aad))
            except Exception:
                raise RuntimeError("响应解密失败 HTTP %s" % code)
        if isinstance(data, dict) and isinstance(data.get("status"), int) \
                and data.get("status") >= 400 and isinstance(data.get("code"), str):
            code = int(data.get("status"))
        if code >= 400:
            msg = ""
            if isinstance(data, dict):
                msg = data.get("title") or data.get("message") or data.get("code") or ""
            raise RuntimeError("荐片接口 HTTP %d %s" % (code, msg))
        return data

    # 首页/分类是静态数据，进程内缓存 90 秒，避免每次进站都重新签名+解密
    CACHE_PATHS = ("home", "catalog/categories")
    CACHE_TTL = 90

    def get(self, path, query=None):
        import json as _json
        key = path + "|" + _json.dumps(query or {}, sort_keys=True, ensure_ascii=False)
        if path in self.CACHE_PATHS:
            hit = getattr(self, "_cache", {}).get(key)
            if hit and (time.time() - hit[0]) < self.CACHE_TTL:
                return hit[1]
        # 内存没命中就查本地持久缓存（重启 App 后第一次进站也能秒开）
        if path in self.CACHE_PATHS and path == "home":
            try:
                raw = self.local.get("jp_home_cache") or ""
                if raw:
                    blob = _json.loads(raw)
                    if (time.time() - float(blob.get("t") or 0)) < 600 and isinstance(blob.get("d"), dict):
                        if not hasattr(self, "_cache"):
                            self._cache = {}
                        self._cache[key] = (time.time(), blob["d"])
                        return blob["d"]
            except Exception:
                pass
        data = self._request("GET", path, query)
        if path in self.CACHE_PATHS:
            if not hasattr(self, "_cache"):
                self._cache = {}
            self._cache[key] = (time.time(), data)
            if path == "home":
                try:
                    self.local.set("jp_home_cache", _json.dumps({"t": int(time.time()), "d": data}, ensure_ascii=False))
                except Exception:
                    pass
        return data

    def post(self, path, body, query=None):
        return self._request("POST", path, query, body)

    # ---------------- 卡片 ----------------
    @staticmethod
    def _sane_year(*cands):
        """只认 1900 ~ 当前年份，未来的年份是源站脏数据（如 2030），直接丢掉。"""
        now = time.localtime().tm_year
        for cand in cands:
            s = str(cand or "")[:4]
            if s.isdigit() and 1900 <= int(s) <= now:
                return s
        return ""

    @classmethod
    def _card(cls, w):
        wid = w.get("id") or w.get("work_id")
        rd = str(w.get("release_date") or "")
        # 上映年份优先 release_date；不合法再退 year；都超未来就不标年份
        year = cls._sane_year(rd[:4], w.get("year"), str(w.get("published_at") or "")[:4])
        return {
            "vod_id": str(wid),
            "vod_name": w.get("title") or "",
            "vod_pic": w.get("poster_url") or "",
            "vod_remarks": w.get("remarks") or "",
            "vod_year": year,
            "vod_pubdate": rd,
            "vod_area": w.get("area") or "",
            "type_name": w.get("kind") or "",
        }

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        home = self.get("home")
        classes = [{"type_id": c.get("category_key"), "type_name": c.get("name")}
                   for c in home.get("categories", []) if c.get("category_key")]
        filters = {}
        for c in home.get("categories", []):
            groups = ((c.get("filter_schema") or {}).get("groups") or [])
            rows = []
            for g in groups:
                is_year = (g.get("key") == "year") or ("年份" in str(g.get("label") or ""))
                now = time.localtime().tm_year
                vals = [{"n": "全部", "v": ""}]
                for o in (g.get("options") or []):
                    v = o.get("value")
                    if not v:
                        continue
                    # 源站年份选项里混了 2027~2033 这类未来年份，只保留今年及以前
                    if is_year and str(v).isdigit() and int(v) > now:
                        continue
                    vals.append({"n": o.get("label"), "v": v})
                if len(vals) > 1:
                    rows.append({"key": g.get("key"), "name": g.get("label"), "init": "", "value": vals})
            if rows:
                filters[c.get("category_key")] = rows
        videos = [self._card(w) for w in (home.get("latest") or [])[:30]]
        if not videos:
            videos = [self._card(w) for w in (home.get("ranking") or [])[:30]] if isinstance(home.get("ranking"), list) else []
        return {"class": classes, "filters": filters, "list": videos}

    # ---------------- 分类 ----------------
    def _result(self, items, page, limit, more):
        # 荐片只有游标没有总页数，用 next_cursor 判断还有没有下一页
        if more:
            total = page * limit
        else:
            total = (page - 1) * limit + len(items)
        return {"page": page, "pagecount": page + 1 if more else page,
                "limit": limit, "total": total, "list": items}

    def categoryContent(self, tid, pg, filter, extend):
        body = dict(extend or {})
        body["category"] = tid
        body.pop("page", None)
        body.pop("cursor", None)
        try:
            page = max(1, int(pg))
        except (TypeError, ValueError):
            page = 1
        cursor = None
        data = {}
        for _ in range(min(page, 12)):
            q = dict(body)
            q["page_size"] = 24
            if cursor:
                q["cursor"] = cursor
            data = self.get("catalog/works", q)
            cursor = data.get("next_cursor")
            if not cursor:
                break
        items = [self._card(w) for w in data.get("items", [])]
        return self._result(items, page, 24, bool(cursor))

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        try:
            page = max(1, int(pg))
        except (TypeError, ValueError):
            page = 1
        data = self.get("search", {"q": key, "page": page, "page_size": 24})
        items = [self._card(w) for w in data.get("items", [])]
        total = data.get("found")
        more = bool(total) and isinstance(total, int) and page * 24 < total
        if not isinstance(total, int) or total <= 0:
            more = len(items) >= 24
        return self._result(items, page, 24, more)

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        out = []
        for wid in ids:
            work = self.get("works/" + quote(str(wid), safe=""))
            eps = (self.get("works/%s/episodes" % quote(str(wid), safe=""),
                            {"page": 1, "page_size": 500}).get("items") or [])
            if not eps:
                eps = [{"index": 0, "key": "1", "name": "正片"}]
            idx0 = eps[0].get("index") or 0
            lines = (self.get("works/%s/media-lines" % quote(str(wid), safe=""),
                              {"episode_index": idx0}).get("items") or [])
            lines = [l for l in lines if l.get("key")]
            if not lines:
                lines = [{"key": "", "name": "荐片"}]
            froms, urls = [], []
            for line in lines:
                names = []
                for e in eps:
                    label = (e.get("name") or str(e.get("index"))).replace("$", "＄").replace("#", "＃")
                    names.append("%s$%s|%s|%s" % (label, wid, e.get("index"), line.get("key")))
                froms.append(line.get("name") or line.get("key"))
                urls.append("#".join(names))
            credits = work.get("credits") or []
            actors = " ".join(c.get("name", "") for c in credits if c.get("role") == "actor")
            directors = " ".join(c.get("name", "") for c in credits if c.get("role") == "director")
            item = self._card(work)
            item.update({
                "vod_id": str(wid),
                "vod_content": work.get("summary") or "",
                "vod_director": directors,
                "vod_actor": actors,
                "vod_play_from": "$$$".join(froms),
                "vod_play_url": "$$$".join(urls),
            })
            out.append(item)
        return {"list": out}

    # ---------------- 播放 ----------------
    def playerContent(self, flag, pid, vipFlags):
        try:
            wid, ep, line = str(pid).split("|")
        except ValueError:
            return {"parse": 0, "url": "", "msg": "播放值格式不正确"}
        data = self.post("media/access", {
            "work_id": int(wid) if str(wid).isdigit() else wid,
            "episode_index": int(ep),
            "line_key": line,
            "delivery_type": "playback",
        })
        url = data.get("url") or ""
        if not url:
            return {"parse": 0, "url": "", "msg": "该线路未返回播放地址"}
        return {"parse": 0, "url": url, "format": "application/x-mpegURL",
                "header": {"User-Agent": UA, "Referer": self.base + "/"}}

    # ---------------- 其它 ----------------
    def homeVideoContent(self):
        return {"list": [self._card(w) for w in (self.get("home").get("latest") or [])[:30]]}

    def isVideoFormat(self, url):
        return any(k in (url or "") for k in (".m3u8", ".mp4"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
