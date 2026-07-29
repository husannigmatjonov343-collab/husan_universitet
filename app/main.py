"""FastAPI ilova — universitetlar sayti."""
from pathlib import Path
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .data import universities as uni_repo
from .data.translations import TRANSLATIONS, t, country_name, COUNTRY_NAMES

BASE = Path(__file__).parent
app = FastAPI(title="UniWorld")

app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

SUPPORTED_LANGS = ("uz", "ru", "en")


def get_lang(lang: str | None) -> str:
    return lang if lang in SUPPORTED_LANGS else "uz"


def base_ctx(request: Request, lang: str) -> dict:
    return {
        "request": request,
        "lang": lang,
        "t": lambda key: t(lang, key),
        "country_name": lambda code: country_name(code, lang),
        "supported_langs": SUPPORTED_LANGS,
        "current_path": request.url.path,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request, lang: str = Query("uz")):
    lang = get_lang(lang)
    all_unis = uni_repo.get_all()
    featured = sorted(all_unis, key=lambda u: u["ranking"])[:6]
    ctx = base_ctx(request, lang)
    ctx.update({
        "featured": featured,
        "total_universities": len(all_unis),
        "total_countries": len(uni_repo.all_countries()),
        "total_faculties": uni_repo.total_faculties(),
        "total_students": uni_repo.total_students(),
    })
    return templates.TemplateResponse(request, "index.html", ctx)


@app.get("/universities", response_class=HTMLResponse)
def universities(
    request: Request,
    lang: str = Query("uz"),
    q: str = Query(""),
    country: str = Query(""),
    sort: str = Query("name"),
):
    lang = get_lang(lang)
    results = uni_repo.search(q, lang) if q else uni_repo.get_all()
    if country:
        results = [u for u in results if u["country"] == country]
    if sort == "year":
        results = sorted(results, key=lambda u: u["founded"])
    elif sort == "students":
        results = sorted(results, key=lambda u: -u["students"])
    else:
        results = sorted(results, key=lambda u: u["name"].get(lang, u["name"]["en"]).lower())
    ctx = base_ctx(request, lang)
    ctx.update({
        "results": results,
        "query": q,
        "country_filter": country,
        "sort": sort,
        "countries": uni_repo.all_countries(),
    })
    return templates.TemplateResponse(request, "universities.html", ctx)


@app.get("/universities/{uni_id}", response_class=HTMLResponse)
def university_detail(request: Request, uni_id: str, lang: str = Query("uz")):
    lang = get_lang(lang)
    uni = uni_repo.get_by_id(uni_id)
    if not uni:
        return RedirectResponse("/universities?lang=" + lang)
    ctx = base_ctx(request, lang)
    similar = [u for u in uni_repo.get_by_country(uni["country"]) if u["id"] != uni["id"]][:3]
    ctx.update({"uni": uni, "similar": similar})
    return templates.TemplateResponse(request, "university.html", ctx)


@app.get("/countries", response_class=HTMLResponse)
def countries(request: Request, lang: str = Query("uz")):
    lang = get_lang(lang)
    ctx = base_ctx(request, lang)
    data = []
    for code, count in sorted(uni_repo.all_countries().items(), key=lambda x: -x[1]):
        data.append({"code": code, "count": count, "sample": uni_repo.get_by_country(code)[:1]})
    ctx["countries_data"] = data
    return templates.TemplateResponse(request, "countries.html", ctx)


@app.get("/about", response_class=HTMLResponse)
def about(request: Request, lang: str = Query("uz")):
    lang = get_lang(lang)
    ctx = base_ctx(request, lang)
    ctx.update({
        "total_universities": len(uni_repo.get_all()),
        "total_countries": len(uni_repo.all_countries()),
    })
    return templates.TemplateResponse(request, "about.html", ctx)


@app.get("/profile")
def profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})
