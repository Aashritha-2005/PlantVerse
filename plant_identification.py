# [1] Imports
import streamlit as st
import requests
from PIL import Image
from transformers import pipeline
from functools import lru_cache

# [2] Language Setup
LANGUAGES = {
    "English": "en",
    "हिन्दी (Hindi)": "hi",
    "తెలుగు (Telugu)": "te",
    "தமிழ் (Tamil)": "ta",
}

# [3] Translate Function
def translate_text(text, target_lang):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data[0][0][0]
    except:
        return text

# [4] Classifier
@st.cache_resource
def load_classifier():
    return pipeline("image-classification", model="Sisigoks/FloraSense")

def predict_species(image: Image.Image):
    classifier = load_classifier()
    if image.mode != "RGB":
        image = image.convert("RGB")
    preds = classifier(image)
    return preds[0]["label"], preds[0]["score"]

# [5] Wikipedia Search
@st.cache_data
def get_wikipedia_title(name: str):
    url = "https://en.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "search", "srsearch": name, "format": "json"}
    data = requests.get(url, params=params, timeout=10).json()
    return data["query"]["search"][0]["title"] if data["query"]["search"] else name

# [6] Wikidata Taxonomy
@st.cache_data
def get_taxonomy_from_wikidata(label: str):
    search = requests.get(
        "https://www.wikidata.org/w/api.php",
        params={"action": "wbsearchentities", "search": label, "language": "en", "format": "json"},
        timeout=5
    ).json()
    if not search.get("search"):
        return {"error": f"No Wikidata entity for '{label}'."}
    eid = search["search"][0]["id"]

    @lru_cache(None)
    def fetch(e):
        return requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{e}.json", timeout=5).json()["entities"][e]

    def find_taxon(e, depth=0):
        if depth > 5: return None
        ent = fetch(e)
        if "P225" in ent.get("claims", {}) and "P171" in ent["claims"]:
            return e
        for prop in ("P31", "P279"):
            for cl in ent.get("claims", {}).get(prop, []):
                nid = cl["mainsnak"]["datavalue"]["value"]["id"]
                res = find_taxon(nid, depth + 1)
                if res: return res
        return None

    taxon_e = find_taxon(eid)
    if not taxon_e: return {"error": f"No taxon root for '{eid}'."}

    taxonomy = {}
    def collect(e, lvl=0):
        if lvl > 20: return
        ent = fetch(e)
        sci = ent.get("claims", {}).get("P225", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
        rank_id = ent.get("claims", {}).get("P105", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "")
        rank = fetch(rank_id).get("labels", {}).get("en", {}).get("value", "") if rank_id else ""
        if sci: taxonomy[rank.capitalize() or f"Rank{lvl}"] = sci
        parent = ent.get("claims", {}).get("P171", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
        if parent: collect(parent, lvl + 1)

    collect(taxon_e)
    return taxonomy

# [7] Medicinal Uses from Wikipedia
def get_medicinal_uses_from_wikipedia(title: str, target_lang="en"):
    try:
        url = "https://en.wikipedia.org/w/api.php"
        sections = requests.get(url, params={
            "action": "parse", "page": title, "prop": "sections", "format": "json"
        }, timeout=10).json().get("parse", {}).get("sections", [])

        section_index = next((sec["index"] for sec in sections if "medicinal" in sec["line"].lower() or "traditional medicine" in sec["line"].lower()), None)
        if not section_index: return None

        html = requests.get(url, params={
            "action": "parse", "page": title, "format": "json",
            "prop": "text", "section": section_index
        }, timeout=10).json().get("parse", {}).get("text", {}).get("*", "")

        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.find_all("p")
        bullet_points = []

        for p in paragraphs:
            text = p.get_text().strip()
            text = re.sub(r"\[\d+\]", "", text)
            if len(text.split()) < 5: continue
            for sent in re.split(r"\.\s+", text):
                sent = sent.strip().strip('.')
                if len(sent.split()) >= 5 and not sent.lower().startswith("there is insufficient"):
                    if target_lang != "en":
                        sent = translate_text(sent, target_lang)
                    bullet_points.append(f"{sent}.")
        return bullet_points[:5] if bullet_points else None
    except Exception:
        return None

# [8] Main UI
def main():
    st.set_page_config(page_title="PlantVerse", layout="wide")

    selected_lang = st.selectbox("🌐 Select Language", list(LANGUAGES.keys()))
    lang_code = LANGUAGES[selected_lang]

    st.title(translate_text("PlantVerse AR", lang_code))

    st.subheader("📷 " + translate_text("Upload a plant image", lang_code))
    st.markdown("📂 " + translate_text("Click 'Browse files' below to upload", lang_code))

    img_file = st.file_uploader("", type=["jpg", "jpeg", "png"])
    if img_file:
        img = Image.open(img_file)
        st.image(img, caption="📸", use_container_width=True)

        if st.button(translate_text("Predict", lang_code)):
            with st.spinner(translate_text("Identifying plant...", lang_code)):
                label, score = predict_species(img)
                wiki_title = get_wikipedia_title(label)
                translated_title = translate_text(wiki_title, lang_code)
                st.info(f"{translate_text('Wikipedia Title', lang_code)}: **{translated_title}**")

                taxonomy = get_taxonomy_from_wikidata(wiki_title)
                st.subheader(translate_text("Taxonomy Tree", lang_code))
                if "error" in taxonomy:
                    st.warning(translate_text(taxonomy["error"], lang_code))
                else:
                    for r, v in taxonomy.items():
                        st.markdown(f"**{translate_text(r, lang_code)}:** {translate_text(v, lang_code)}")

                st.subheader(translate_text("💊 Uses", lang_code))

                med_use = get_medicinal_uses_from_wikipedia(wiki_title, target_lang=lang_code)
                if med_use:
                    for point in med_use:
                        st.markdown(f"- {point}")
                else:
                    st.info(translate_text("No specific medicinal uses found.", lang_code))

if __name__ == "__main__":
    main()

# # [1] Imports
# import streamlit as st
# import requests
# from PIL import Image
# from transformers import pipeline
# from functools import lru_cache

# # [2] Language Setup
# LANGUAGES = {
#     "English": "en",
#     "हिन्दी (Hindi)": "hi",
#     "తెలుగు (Telugu)": "te",
#     "தமிழ் (Tamil)": "ta",
# }

# # [3] Translate Function
# def translate_text(text, target_lang):
#     try:
#         url = "https://translate.googleapis.com/translate_a/single"
#         params = {
#             "client": "gtx",
#             "sl": "en",
#             "tl": target_lang,
#             "dt": "t",
#             "q": text
#         }
#         response = requests.get(url, params=params, timeout=10)
#         data = response.json()
#         return data[0][0][0]
#     except:
#         return text

# # [4] Classifier
# @st.cache_resource
# def load_classifier():
#     return pipeline("image-classification", model="Sisigoks/FloraSense")

# def predict_species(image: Image.Image):
#     classifier = load_classifier()
#     if image.mode != "RGB":
#         image = image.convert("RGB")
#     preds = classifier(image)
#     return preds[0]["label"], preds[0]["score"]

# # [5] Wikipedia Search
# @st.cache_data
# def get_wikipedia_title(name: str):
#     url = "https://en.wikipedia.org/w/api.php"
#     params = {"action": "query", "list": "search", "srsearch": name, "format": "json"}
#     data = requests.get(url, params=params, timeout=10).json()
#     return data["query"]["search"][0]["title"] if data["query"]["search"] else name

# # [6] Wikidata Taxonomy
# @st.cache_data
# def get_taxonomy_from_wikidata(label: str):
#     search = requests.get(
#         "https://www.wikidata.org/w/api.php",
#         params={"action": "wbsearchentities", "search": label, "language": "en", "format": "json"},
#         timeout=5
#     ).json()
#     if not search.get("search"):
#         return {"error": f"No Wikidata entity for '{label}'."}
#     eid = search["search"][0]["id"]

#     @lru_cache(None)
#     def fetch(e):
#         url = f"https://www.wikidata.org/wiki/Special:EntityData/{e}.json"
#     try:
#         response = requests.get(url, timeout=5)
#         response.raise_for_status()  # Raises HTTPError if status is not 200
#         data = response.json()
#         return data["entities"][e]
#     except Exception as err:
#         print(f"❌ Failed to fetch Wikidata entity {e}: {err}")
#         return {}  # or return None

#     def find_taxon(e, depth=0):
#         if depth > 5: return None
#         ent = fetch(e)
#         if "P225" in ent.get("claims", {}) and "P171" in ent["claims"]:
#             return e
#         for prop in ("P31", "P279"):
#             for cl in ent.get("claims", {}).get(prop, []):
#                 nid = cl["mainsnak"]["datavalue"]["value"]["id"]
#                 res = find_taxon(nid, depth + 1)
#                 if res: return res
#         return None

#     taxon_e = find_taxon(eid)
#     if not taxon_e: return {"error": f"No taxon root for '{eid}'."}

#     taxonomy = {}
#     def collect(e, lvl=0):
#         if lvl > 20: return
#         ent = fetch(e)
#         sci = ent.get("claims", {}).get("P225", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
#         rank_id = ent.get("claims", {}).get("P105", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "")
#         rank = fetch(rank_id).get("labels", {}).get("en", {}).get("value", "") if rank_id else ""
#         if sci: taxonomy[rank.capitalize() or f"Rank{lvl}"] = sci
#         parent = ent.get("claims", {}).get("P171", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
#         if parent: collect(parent, lvl + 1)

#     collect(taxon_e)
#     return taxonomy

# # [7] Medicinal Uses from Wikipedia
# def get_medicinal_uses_from_wikipedia(title: str, target_lang="en"):
#     try:
#         url = "https://en.wikipedia.org/w/api.php"
#         sections = requests.get(url, params={
#             "action": "parse", "page": title, "prop": "sections", "format": "json"
#         }, timeout=10).json().get("parse", {}).get("sections", [])

#         section_index = next((sec["index"] for sec in sections if "medicinal" in sec["line"].lower() or "traditional medicine" in sec["line"].lower()), None)
#         if not section_index: return None

#         html = requests.get(url, params={
#             "action": "parse", "page": title, "format": "json",
#             "prop": "text", "section": section_index
#         }, timeout=10).json().get("parse", {}).get("text", {}).get("*", "")

#         from bs4 import BeautifulSoup
#         import re
#         soup = BeautifulSoup(html, "html.parser")
#         paragraphs = soup.find_all("p")
#         bullet_points = []

#         for p in paragraphs:
#             text = p.get_text().strip()
#             text = re.sub(r"\[\d+\]", "", text)
#             if len(text.split()) < 5: continue
#             for sent in re.split(r"\.\s+", text):
#                 sent = sent.strip().strip('.')
#                 if len(sent.split()) >= 5 and not sent.lower().startswith("there is insufficient"):
#                     if target_lang != "en":
#                         sent = translate_text(sent, target_lang)
#                     bullet_points.append(f"{sent}.")
#         return bullet_points[:5] if bullet_points else None
#     except Exception:
#         return None

# # [8] Main UI
# def main():
#     st.set_page_config(page_title="PlantVerse", layout="wide")

#     selected_lang = st.selectbox("🌐 Select Language", list(LANGUAGES.keys()))
#     lang_code = LANGUAGES[selected_lang]

#     st.title(translate_text("PlantVerse AR", lang_code))

#     st.subheader("📷 " + translate_text("Upload a plant image", lang_code))
#     st.markdown("📂 " + translate_text("Click 'Browse files' below to upload", lang_code))

#     img_file = st.file_uploader("", type=["jpg", "jpeg", "png"])
#     if img_file:
#         img = Image.open(img_file)
#         st.image(img, caption="📸", use_container_width=True)

#         if st.button(translate_text("Predict", lang_code)):
#             with st.spinner(translate_text("Identifying plant...", lang_code)):
#                 label, score = predict_species(img)
#                 wiki_title = get_wikipedia_title(label)
#                 translated_title = translate_text(wiki_title, lang_code)
#                 st.info(f"{translate_text('Wikipedia Title', lang_code)}: **{translated_title}**")

#                 taxonomy = get_taxonomy_from_wikidata(wiki_title)
#                 st.subheader(translate_text("Taxonomy Tree", lang_code))
#                 if "error" in taxonomy:
#                     st.warning(translate_text(taxonomy["error"], lang_code))
#                 else:
#                     for r, v in taxonomy.items():
#                         st.markdown(f"**{translate_text(r, lang_code)}:** {translate_text(v, lang_code)}")

#                 st.subheader(translate_text("💊 Uses", lang_code))

#                 med_use = get_medicinal_uses_from_wikipedia(wiki_title, target_lang=lang_code)
#                 if med_use:
#                     for point in med_use:
#                         st.markdown(f"- {point}")
#                 else:
#                     st.info(translate_text("No specific medicinal uses found.", lang_code))

# if __name__ == "__main__":
#     main()
