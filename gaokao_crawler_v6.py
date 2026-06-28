import asyncio, aiohttp, json, os, time, subprocess

API_URL = "https://api-gaokao.zjzw.cn/apidata/web"
YEAR = 2025
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gaokao_data")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "_checkpoint_v2.json")
CSV_FILE = os.path.join(DATA_DIR, "_all_data.csv")
COOKIE_FILE = os.path.join(BASE_DIR, "_waf_cookies.json")
NODE_SCRIPT = os.path.join(BASE_DIR, "get_cookies.js")
os.makedirs(DATA_DIR, exist_ok=True)

API_SEM_SIZE = 30
SCHOOL_CONCURRENCY = 15
COOKIE_HEADER = ""
COOKIE_READY = asyncio.Event()

ALL_PROVINCES = [11,12,13,14,15,21,22,23,31,32,33,34,35,36,37,
                 41,42,43,44,45,46,50,51,52,53,54,61,62,63,64,65]


def sync_refresh():
    global COOKIE_HEADER
    try:
        r = subprocess.run(["node", NODE_SCRIPT], capture_output=True,
                           text=True, timeout=30, cwd=BASE_DIR)
        if r.returncode != 0:
            return False
        c = json.loads(r.stdout.strip())
        COOKIE_HEADER = "; ".join(f"{k}={v}" for k, v in c.items())
        json.dump(c, open(COOKIE_FILE, "w"))
        print(f"\n[COOKIE] OK keys={list(c.keys())}", flush=True)
        return True
    except Exception as e:
        print(f"\n[COOKIE] err={e}", flush=True)
    return False


async def cookie_loop():
    while True:
        ok = await asyncio.get_running_loop().run_in_executor(None, sync_refresh)
        if ok:
            COOKIE_READY.set()
        await asyncio.sleep(900)


def hdr():
    return {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0",
        "Origin": "https://www.gaokao.cn",
        "Referer": "https://www.gaokao.cn/",
        "Cookie": COOKIE_HEADER,
    }


async def api_post(session, params, sem, retries=3):
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    url = f"{API_URL}?{qs}&signsafe=x"
    body = json.dumps({**params, "signsafe": "x"}).encode()
    for _ in range(retries):
        async with sem:
            try:
                async with session.post(url, data=body, headers=hdr(),
                                        timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    text = await resp.text()
                    if text.startswith("{"):
                        return json.loads(text)
            except:
                pass
        # HTML or err → wait for next cookie refresh
        await COOKIE_READY.wait()
        await asyncio.sleep(0.5)
    return None


async def get_config(session, sid):
    url = f"https://static-data.gaokao.cn/www/2.0/school/{sid}/dic/professionalscore.json?a=www.gaokao.cn"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            d = await resp.json()
    except:
        return [], {}
    if d.get("code") != "0000":
        return [], {}
    n = d["data"]["newsdata"]
    cfg = {}
    for k, v in (n.get("type") or {}).items():
        cfg[k] = v if isinstance(v, list) else [v]
    for k, v in (n.get("batch") or {}).items():
        cfg[k] = v if isinstance(v, list) else [v]
    return n.get("province", []), cfg


async def crawl_province(session, sem, sid, pid, types, cfg):
    pr, sr = [], []
    for tid in types:
        p = dict(autosign="", local_province_id=str(pid), local_type_id=str(tid),
                 page="1", platform="2", school_id=str(sid), size="200",
                 uri="v1/school/province_score", year=str(YEAR))
        d = await api_post(session, p, sem)
        if d and d.get("code") == 0:
            for it in d["data"].get("item", []):
                it["local_type_id"] = tid
                it["local_province_id"] = pid
            pr.extend(d["data"].get("item", []))

        for bid in cfg.get(f"{pid}_{YEAR}_{tid}", [14, 7]):
            p = dict(autosign="", like_spname="", local_batch_id=str(bid),
                     local_province_id=str(pid), local_type_id=str(tid),
                     page="1", platform="2", school_id=str(sid),
                     sg_xuanke="", size="200", special_group="",
                     uri="v1/school/special_score", year=str(YEAR))
            d = await api_post(session, p, sem)
            if d and d.get("code") == 0:
                for it in d["data"].get("item", []):
                    it["local_type_id"] = tid
                    it["local_province_id"] = pid
                    it["local_batch_id"] = bid
                sr.extend(d["data"].get("item", []))
    return pr, sr


def save(sid, sname, level, sprovince, recs):
    if not recs:
        return
    clean = "".join(c if c.isalnum() or c in " _-" else "_" for c in sname)
    fp = os.path.join(DATA_DIR, f"{sid:05d}_{clean}.json")
    json.dump(dict(id=sid, name=sname, level=level, province=sprovince,
                   year=YEAR, count=len(recs), records=recs),
              open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    is_new = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", encoding="utf-8") as f:
        if is_new:
            f.write("学校ID|学校名称|学校层次|学校所在地|年份|省份ID|省份|科类ID|科类|批次ID|批次|招生类型|"
                     "专业名称|专业备注|最低分|最低位次|平均分|录取人数|批次线|分差|专业组|选科要求|数据来源\n")
        for r in recs:
            im = "sp_name" in r
            f.write("|".join([
                str(sid), sname, level, sprovince,
                str(r.get("year","")),
                str(r.get("local_province_id","")),
                r.get("local_province_name",""),
                str(r.get("local_type_id","")),
                r.get("local_type_name",""),
                str(r.get("local_batch_id","")),
                r.get("local_batch_name",""),
                r.get("zslx_name",""),
                r.get("sp_name","") if im else "",
                r.get("remark","") if im else "",
                str(r.get("min","")),
                str(r.get("min_section","")),
                str(r.get("average","")),
                str(r.get("lq_num","")) if im else str(r.get("num","")),
                str(r.get("proscore","")),
                str(r.get("diff","")),
                r.get("sg_name",""),
                r.get("sg_info","") or r.get("xclevel_name",""),
                "special_score" if im else "province_score",
            ]) + "\n")


async def crawl_one(session, sem, sid, sname, level, sprovince):
    pl, cfg = await get_config(session, sid)
    if not pl:
        pl = ALL_PROVINCES
    tasks = [crawl_province(session, sem, sid, pid,
                            cfg.get(f"{pid}_{YEAR}", cfg.get(f"{pid}_2024", [])) or [1, 2], cfg)
             for pid in pl]
    all_recs = []
    for pr, sr in await asyncio.gather(*tasks):
        all_recs.extend(pr)
        all_recs.extend(sr)
    if all_recs:
        save(sid, sname, level, sprovince, all_recs)
    return len(all_recs)


async def main():
    print("=" * 60, flush=True)
    print(f"掌上高考 {YEAR} V6（page.goto WAF + 30并发 + 15学校并行）", flush=True)
    print("=" * 60, flush=True)

    asyncio.create_task(cookie_loop())
    print("等待首次 cookie 就绪...", flush=True)
    await asyncio.wait_for(COOKIE_READY.wait(), timeout=30)
    print("Cookie 就绪!", flush=True)

    print("加载学校列表...", flush=True)
    async with aiohttp.ClientSession() as s:
        r = await s.get(
            "https://static-data.gaokao.cn/www/2.0/school/list_v2.json?a=www.gaokao.cn",
            timeout=aiohttp.ClientTimeout(total=30))
        raw = await r.json()
    all_schools = raw.get("data", {})
    total = len(all_schools)
    print(f"共 {total} 所学校", flush=True)

    checkpoint = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            checkpoint = json.load(f)
    completed = set(checkpoint.get("completed", []))
    print(f"已完成 {len(completed)} 所", flush=True)

    sem = asyncio.Semaphore(API_SEM_SIZE)
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
    pending = {}
    done = len(completed)
    t0 = time.time()
    nth = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        for idx_str, info in sorted(all_schools.items(), key=lambda x: int(x[0])):
            sid = int(idx_str)
            if sid in completed:
                continue

            while len(pending) >= SCHOOL_CONCURRENCY:
                dd, _ = await asyncio.wait(pending.values(), return_when=asyncio.FIRST_COMPLETED)
                for t in dd:
                    for k, v in list(pending.items()):
                        if v is t:
                            cnt = v.result()
                            done += 1
                            el = time.time() - t0
                            rps = done / el * 60
                            print(f"[{done}/{total}] {k[1]}: {cnt}条 | {el/60:.0f}min | {rps:.0f}所/分", flush=True)
                            del pending[k]
                            break
                break

            t = asyncio.create_task(crawl_one(session, sem, sid,
                info.get("name", f"未知{sid}"), info.get("level", ""), info.get("p", "")))
            pending[(sid, info.get("name", ""))] = t

        while pending:
            dd, _ = await asyncio.wait(pending.values(), return_when=asyncio.FIRST_COMPLETED)
            for t in dd:
                for k, v in list(pending.items()):
                    if v is t:
                        cnt = v.result()
                        done += 1
                        el = time.time() - t0
                        sname = k[1]
                        # 每50所学校保存 checkpiont
                        nth += 1
                        if nth % 50 == 0:
                            completed.add(k[0])
                            json.dump({"completed": list(completed)}, open(CHECKPOINT_FILE, "w"))
                        rps = done / el * 60
                        eta_min = (total - done) / (done / el) / 60
                        print(f"[{done}/{total}] {sname}: {cnt}条 | {el/60:.0f}min | {rps:.0f}所/分 | ETA {eta_min:.0f}分", flush=True)
                        del pending[k]
                        break

        # final checkpoint
        json.dump({"completed": list(completed)}, open(CHECKPOINT_FILE, "w"))

    print(f"\n完成! 耗时{(time.time()-t0)/60:.1f}分", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
