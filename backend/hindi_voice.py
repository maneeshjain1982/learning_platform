"""Hindi Voice tab: what it takes to add Hindi (or any new language) to a voice assistant's ASR and NLU.

Curated and checked on CHECKED_ON: every URL was opened, every arXiv ID was checked against the arXiv API, licences
come from the Hugging Face model/dataset cards, and WER figures are quoted only from the source named next to them.
Bixby specifics come from the public Bixby developer docs only (no internal Samsung process).
"""

from __future__ import annotations

CHECKED_ON = "2026-11-12"
PATH_SLUG = "hindi-voice-asr-nlu"
PATH_TITLE = "Hindi Voice Assistant: ASR + NLU"
PATH_SUMMARY = ("What you need to add Hindi to a voice assistant: speech basics, ASR models, Hindi text "
                "normalization, language models and biasing, on-device speech, intent and slot NLU, Hinglish and "
                "transliteration, entities, LLM-based NLU, data, evaluation and launch.")

ARXIV = "https://arxiv.org/abs/"

# ------------------------------------------------------------------ competencies
# need: 1 basic, 2 working, 3 strong, 4 expert (for the person leading the language launch)

COMPETENCIES = [
    {"id": "speech", "title": "Speech and signal basics", "skills": [
        ("Phonetics and phonology of Hindi", 3, "Aspirated vs unaspirated stops (क/ख), retroflex vs dental (ट/त), "
         "nasalisation and schwa deletion drive both lexicon design and the errors you will see."),
        ("Audio features and front-end", 2, "Sampling rates, log-mel features, VAD and AGC: most 'model' bugs on "
         "devices turn out to be front-end mismatches."),
        ("Acoustics of real devices", 2, "Far-field, echo cancellation and noise suppression change what the model "
         "hears; test data must match."),
    ]},
    {"id": "asr", "title": "ASR modelling", "skills": [
        ("End-to-end ASR (CTC, RNN-T, attention)", 3, "Today's production models; you must pick the right loss and "
         "decoder for streaming vs offline."),
        ("Self-supervised and multilingual pre-training", 3, "wav2vec 2.0, MMS, Whisper and IndicConformer let you "
         "start Hindi from a strong multilingual base instead of from scratch."),
        ("Language models, decoding and contextual biasing", 3, "Contact names, app names and Hindi numerals are "
         "where generic models fail; biasing fixes them."),
        ("Fine-tuning toolkits (NeMo, ESPnet, k2/icefall, Hugging Face)", 3, "You will train and fine-tune with one "
         "of these."),
        ("Streaming and on-device optimisation", 2, "Quantisation, chunked attention, latency budgets, wake word and "
         "endpointing."),
    ]},
    {"id": "nlu", "title": "NLU and language understanding", "skills": [
        ("Intent classification and slot filling", 4, "The core of an assistant's NLU, and the thing every new "
         "language needs trained and tested."),
        ("Multilingual encoders (MuRIL, IndicBERT v2, XLM-R)", 3, "The usual backbone for Hindi intent and slot "
         "models; they handle Devanagari and transliterated text."),
        ("Code-mixing and transliteration (Hinglish)", 4, "Real Indian users say 'कल सुबह 7 बजे का alarm लगाओ'. "
         "Mixed script and mixed language is the norm, not the edge case."),
        ("Entity resolution and normalization", 3, "Contacts, apps, places, dates, times and number words in Hindi "
         "must map to the same values as other locales."),
        ("LLM-based NLU and distillation", 2, "LLMs bootstrap data and handle long-tail requests; small distilled "
         "models run on device."),
    ]},
    {"id": "language", "title": "Hindi language knowledge", "skills": [
        ("Devanagari Unicode, nukta and normalization", 3, "The same word can be typed several ways (ज़ / ज़, "
         "anusvara vs chandrabindu); without one canonical form your WER and slot F1 are wrong."),
        ("Hindi grammar for NLG (gender, honorifics)", 2, "Responses must agree in gender and use आप-level "
         "politeness; templates need agreement rules."),
        ("Regional variation", 2, "Accent and vocabulary differ across UP, Bihar, Rajasthan, MP, Haryana, Delhi and "
         "non-native speakers from the south and east."),
    ]},
    {"id": "data", "title": "Data engineering", "skills": [
        ("Data collection and annotation design", 4, "Speaker coverage, prompts, transcription conventions and "
         "label guidelines decide quality more than the model does."),
        ("Synthetic data (TTS and LLM generation)", 3, "Fills coverage gaps quickly for new intents and rare "
         "entities, if you control the risks."),
        ("Augmentation (noise, RIR, speed, SpecAugment)", 2, "Cheap robustness to devices and rooms."),
        ("Privacy, consent and licences", 3, "Voice is personal data under India's DPDP Act 2023; dataset licences "
         "(e.g. CC-BY-NC) can block commercial use."),
    ]},
    {"id": "eval", "title": "Evaluation and testing", "skills": [
        ("ASR metrics and slicing (WER, CER, entity WER)", 4, "A single WER hides failures; slice by accent, "
         "noise, device and domain."),
        ("NLU metrics (intent accuracy, slot F1, exact match)", 4, "Plus robustness sets for Hinglish and romanized "
         "input."),
        ("End-to-end task success and human evaluation", 3, "What users feel; the launch gate."),
        ("Statistics for test design", 2, "Sample sizes and confidence intervals so a 0.5% WER change means "
         "something."),
    ]},
    {"id": "platform", "title": "Assistant platform and production", "skills": [
        ("Locale onboarding in the assistant (Bixby capsules)", 3, "Targets per locale, training utterances "
         "(Aligned NL), dialog and resources per locale."),
        ("Serving, latency and monitoring", 2, "Hybrid on-device/cloud routing, dashboards on live traffic, "
         "rollback."),
        ("Continuous improvement loop", 3, "Mining failures from live traffic (with consent), re-labelling and "
         "regular retraining."),
    ]},
]

# ------------------------------------------------------------------ courses

PHASES = [
    {"id": "foundations", "title": "1. Foundations", "summary": "Speech and language processing basics."},
    {"id": "asr", "title": "2. ASR in practice", "summary": "Train, fine-tune and evaluate speech models."},
    {"id": "nlu", "title": "3. NLU and LLMs", "summary": "Transformers, intent and slot models, LLMs."},
    {"id": "indic", "title": "4. Hindi and Indic resources", "summary": "Where the Indic models and data live."},
    {"id": "platform", "title": "5. Assistant platform", "summary": "How a new locale goes into Bixby capsules."},
]


def _course(cid, title, provider, url, phase, *, kind="Course", level="intermediate", cost="Free", covers="",
            top=False):
    return {"id": cid, "title": title, "provider": provider, "url": url, "phase": phase, "kind": kind,
            "level": level, "cost": cost, "covers": covers, "top_pick": top}


COURSES = [
    _course("slp3", "Speech and Language Processing (3rd ed. draft)", "Jurafsky & Martin, Stanford",
            "https://web.stanford.edu/~jurafsky/slp3/", "foundations", kind="Free textbook", level="beginner",
            covers="The standard reference: n-grams, transformers, ASR, TTS, dialogue systems and evaluation. Read "
                   "the ASR and dialogue chapters first.", top=True),
    _course("cs224s", "CS224S: Spoken Language Processing", "Stanford", "https://web.stanford.edu/class/cs224s/",
            "foundations", kind="University course (slides, lectures)",
            covers="Speech recognition, end-to-end ASR, TTS, spoken dialogue and voice assistants.", top=True),
    _course("nptel-dsp", "Digital Speech Processing", "NPTEL · IIT Kharagpur (Prof. S. K. Das Mandal)",
            "https://nptel.ac.in/courses/117105145", "foundations", kind="MOOC with certificate exam",
            cost="Free to learn; certificate exam fee",
            covers="Speech production, acoustics and phonetics, features and classic recognition, taught with "
                   "Indian-language examples."),
    _course("hf-audio", "Hugging Face Audio Course", "Hugging Face", "https://huggingface.co/learn/audio-course",
            "asr", level="beginner",
            covers="Audio data, Whisper and CTC models, fine-tuning ASR on a new language, evaluation with WER. The "
                   "fastest hands-on start.", top=True),
    _course("nemo-asr", "NVIDIA NeMo ASR docs and tutorials", "NVIDIA",
            "https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html", "asr",
            kind="Docs + notebooks", level="advanced",
            covers="Conformer/FastConformer CTC and RNN-T, tokenizers, fine-tuning to a new language, streaming. "
                   "AI4Bharat's IndicConformer is built on a NeMo fork.", top=True),
    _course("espnet", "ESPnet toolkit and recipes", "ESPnet community", "https://espnet.github.io/espnet/", "asr",
            kind="Toolkit docs + recipes", level="advanced",
            covers="Research-grade recipes for ASR, SLU and TTS; many papers publish ESPnet recipes."),
    _course("icefall", "k2 / icefall", "Next-gen Kaldi", "https://k2-fsa.github.io/icefall/", "asr",
            kind="Toolkit docs + recipes", level="advanced",
            covers="Streaming zipformer transducers, and with sherpa-onnx, deployment on Android and embedded "
                   "devices."),
    _course("kaldi", "Kaldi documentation", "Kaldi", "https://kaldi-asr.org/doc/", "asr", kind="Toolkit docs",
            level="advanced",
            covers="WFST decoding, lexicons and classic hybrid ASR. Still useful to understand decoding graphs and "
                   "biasing."),
    _course("hf-llm", "Hugging Face LLM Course", "Hugging Face", "https://huggingface.co/learn/llm-course", "nlu",
            level="beginner",
            covers="Transformers, tokenizers, fine-tuning for token classification (slots) and sequence "
                   "classification (intents)."),
    _course("cs224n", "CS224N: NLP with Deep Learning", "Stanford", "https://web.stanford.edu/class/cs224n/", "nlu",
            kind="University course (slides, lectures)",
            covers="Word vectors to transformers and LLMs; the theory behind modern NLU."),
    _course("seq-models", "Sequence Models (Deep Learning Specialization)", "DeepLearning.AI on Coursera",
            "https://www.coursera.org/learn/nlp-sequence-models", "nlu", kind="MOOC with certificate",
            cost="Free to audit; certificate paid",
            covers="RNNs, attention and a speech trigger-word project; a gentle bridge into speech and NLP."),
    _course("ai4bharat", "AI4Bharat models, datasets and papers", "AI4Bharat, IIT Madras",
            "https://ai4bharat.iitm.ac.in/", "indic", kind="Research lab hub", level="intermediate",
            covers="The main open source of Indic ASR (IndicConformer, IndicWhisper), NLU (IndicBERT, IndicTrans2), "
                   "transliteration (IndicXlit) and datasets (IndicVoices, Kathbath).", top=True),
    _course("bhashini", "Bhashini (National Language Translation Mission)", "Government of India",
            "https://bhashini.gov.in/", "indic", kind="Platform + APIs",
            covers="Government platform with Indic ASR, translation and TTS APIs and datasets; useful as a "
                   "comparison baseline and for data sources."),
    _course("bixby-quick", "Bixby Developer Center: quick start", "Samsung",
            "https://bixbydevelopers.com/dev/docs/get-started/quick-start", "platform", kind="Developer docs",
            level="beginner", covers="Capsules, models, actions and Bixby Developer Studio."),
    _course("bixby-training", "Bixby: training for natural language", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl", "platform",
            kind="Developer docs",
            covers="Training utterances per language, goals and annotations (Aligned NL), and testing them.",
            top=True),
    _course("bixby-language", "Bixby: modeling language and dialog", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.language", "platform",
            kind="Developer docs", covers="How a capsule's language resources are modelled per locale."),
    _course("bixby-variations", "Bixby design guide: writing variations", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/design-guides/writing.variations", "platform",
            kind="Developer docs", covers="Writing response variations; apply it to Hindi dialog with gender and "
                                          "honorific agreement."),
]

# ------------------------------------------------------------------ technical modules (also used for review Q&A)

def _mod(slug, side, title, summary, url, outline, refs=()):
    return {"slug": slug, "side": side, "title": title, "summary": summary, "url": url, "outline": outline,
            "refs": list(refs), "lessons": sum(len(ls) for _, ls in outline)}


MODULES = [
    _mod("hv-speech-basics", "asr", "Speech and audio fundamentals for Hindi",
         "How Hindi sounds become numbers a model can use: phonetics, audio capture, features and voice activity.",
         "https://web.stanford.edu/~jurafsky/slp3/",
         [("Hindi phonetics", ["Hindi consonant system: aspiration, retroflex vs dental, nukta sounds",
                               "Vowels, nasalisation, and schwa deletion in spoken Hindi",
                               "Accents and regional variation in spoken Hindi"]),
          ("Audio front-end", ["Sampling rate, bit depth and codecs on phones and TVs",
                               "Log-mel spectrograms and MFCCs",
                               "Voice activity detection, AGC, noise suppression and echo cancellation"])],
         ["https://nptel.ac.in/courses/117105145", "https://huggingface.co/learn/audio-course"]),
    _mod("hv-asr-models", "asr", "ASR models: CTC, RNN-T, Conformer, Whisper",
         "The model families used for Hindi ASR today, and how to start from a multilingual model.",
         "https://huggingface.co/learn/audio-course",
         [("Architectures", ["CTC: alignment-free training and greedy vs beam decoding",
                             "RNN-Transducer and why assistants use it for streaming",
                             "Attention encoder-decoder models and Whisper",
                             "Conformer and FastConformer encoders"]),
          ("Starting a new language", ["Self-supervised pre-training: wav2vec 2.0 and IndicWav2Vec",
                                       "Multilingual models: MMS, Whisper, USM, IndicConformer",
                                       "Tokenizer choice for Hindi: characters, BPE, SentencePiece",
                                       "Fine-tuning a multilingual model on Hindi data"])],
         [ARXIV + "2005.08100", ARXIV + "2212.04356", ARXIV + "2111.03945"]),
    _mod("hv-hindi-text", "asr", "Hindi text: lexicon, G2P and normalization",
         "Getting one canonical written form, so training labels, WER and slots agree.",
         "https://github.com/anoopkunchukuttan/indic_nlp_library",
         [("Script", ["Devanagari Unicode: nukta, anusvara, chandrabindu, halant, ZWJ/ZWNJ",
                      "Unicode normalization and canonical spelling variants",
                      "Transcription conventions for English words in Hindi speech"]),
          ("Pronunciation", ["Grapheme-to-phoneme rules and schwa deletion", "Pronunciation lexicons for names"]),
          ("Normalization", ["Text normalization (TN) for TTS and LM training",
                             "Inverse text normalization (ITN): दो सौ पचास → 250, dates, times, currency"])],
         ["https://github.com/NVIDIA/NeMo-text-processing", ARXIV + "1611.00068"]),
    _mod("hv-lm-decoding", "asr", "Language models, decoding and contextual biasing",
         "Making the recogniser get assistant-specific words right: contacts, apps, commands.",
         "https://kaldi-asr.org/doc/",
         [("Decoding", ["Beam search and n-gram LMs (KenLM) with CTC", "Shallow fusion and LM weight tuning",
                        "WFST decoding graphs (HCLG) in brief"]),
          ("Biasing", ["Contextual biasing for contacts and app names (CLAS, boosting)",
                       "Domain LMs for assistant commands", "Handling out-of-vocabulary names and rare entities"])],
         [ARXIV + "1808.02480"]),
    _mod("hv-on-device", "asr", "Wake word, endpointing and on-device ASR",
         "The parts that make a voice assistant feel fast: always-on wake word, when the user stopped, and "
         "running on the phone.",
         "https://github.com/k2-fsa/sherpa-onnx",
         [("Always-on", ["Wake-word / keyword spotting models and false-accept trade-offs",
                         "Endpointing: deciding the user finished speaking"]),
          ("Streaming", ["Streaming ASR latency: chunking, look-ahead, partial results",
                         "Hybrid on-device and server ASR routing"]),
          ("Optimisation", ["Quantisation and model compression for phones", "Memory, battery and thermal budgets"])],
         [ARXIV + "1811.06621", ARXIV + "1711.07128"]),
    _mod("hv-nlu-core", "nlu", "Intent classification and slot filling",
         "The core NLU task for a new language: map an utterance to a goal and its arguments.",
         "https://huggingface.co/learn/llm-course",
         [("Task", ["Intents, slots and BIO tagging", "Joint intent-slot models (e.g. BERT-based)",
                    "Hierarchical and compositional parses (MTOP style)"]),
          ("Models for Hindi", ["Multilingual encoders: MuRIL, IndicBERT v2, XLM-R",
                                "Cross-lingual transfer from English training data",
                                "Translate-train vs native Hindi data"]),
          ("Data", ["MASSIVE hi-IN as a benchmark", "Writing annotation guidelines for Hindi slots"])],
         [ARXIV + "1902.10909", ARXIV + "2204.08582", ARXIV + "2008.09335"]),
    _mod("hv-codemix", "nlu", "Hinglish, code-mixing and transliteration",
         "How real Indian users speak and type, and how to make ASR output and NLU agree on it.",
         "https://github.com/AI4Bharat/IndicXlit",
         [("Code-mixing", ["What Hinglish looks like in assistant commands", "Matrix language and switch points",
                           "Code-switched ASR (MUCS 2021)"]),
          ("Script", ["Romanized Hindi input and transliteration (IndicXlit, Aksharantar)",
                      "Choosing one script for NLU input: Devanagari, Roman, or both",
                      "Robustness tests for mixed-script input"])],
         [ARXIV + "2104.00235", ARXIV + "2205.03018", ARXIV + "2004.12376"]),
    _mod("hv-entities", "nlu", "Entities: contacts, apps, places, dates and numbers",
         "Resolving what the user named to a real thing the device can act on.",
         "https://huggingface.co/datasets/ai4bharat/naamapadam",
         [("Recognition", ["Named entity recognition in Hindi (Naamapadam)", "Gazetteers and catalog matching"]),
          ("Resolution", ["Phonetic and fuzzy matching across Devanagari and Roman names",
                          "Hindi number words, dates and times (परसों, सवा पाँच, साढ़े)",
                          "Units, currency and relative expressions"])],
         [ARXIV + "2212.10168"]),
    _mod("hv-llm-nlu", "nlu", "LLMs for Hindi NLU, dialog and responses",
         "Where LLMs help a voice assistant in a new language, and where small models still win.",
         "https://huggingface.co/ai4bharat/Airavata",
         [("Understanding", ["Few-shot and function-calling NLU with LLMs",
                             "Distilling LLM labels into small on-device models",
                             "Indic LLMs: Airavata, Sarvam-1 and multilingual frontier models"]),
          ("Responses", ["Hindi response generation: gender agreement and honorifics",
                         "Localizing dialog templates and variations",
                         "Hindi TTS for responses (IndicTTS, Indic Parler-TTS)"])],
         [ARXIV + "2401.15006", ARXIV + "2211.09536"]),
    _mod("hv-data", "process", "Data strategy for a new language",
         "Getting the right speech and text data: coverage, collection, annotation, synthesis and consent.",
         "https://huggingface.co/datasets/ai4bharat/IndicVoices",
         [("Planning", ["Variability matrix: speakers, accents, devices, noise, domains",
                        "Read vs extempore vs conversational speech", "How many hours and utterances you need"]),
          ("Collection", ["Crowd and vendor collection, prompts and QA",
                          "Transcription and labelling guidelines, inter-annotator agreement"]),
          ("Synthesis", ["Synthetic speech from TTS for ASR", "LLM-generated utterances for NLU",
                         "Augmentation: noise, room impulse responses, speed, SpecAugment"]),
          ("Governance", ["Consent, DPDP Act 2023 and dataset licences"])],
         [ARXIV + "2403.01926", ARXIV + "1909.11699", ARXIV + "1904.08779"]),
    _mod("hv-eval", "process", "Testing and evaluation",
         "How to prove the Hindi assistant works: ASR, NLU and end-to-end tests that a launch can be gated on.",
         "https://github.com/jitsi/jiwer",
         [("ASR", ["WER, CER and why Hindi needs both", "Entity WER and command success",
                   "Slicing by accent, gender, age, noise, device and domain", "Benchmarks: Vistaar, Lahaja, FLEURS"]),
          ("NLU", ["Intent accuracy, slot F1 and exact match", "Robustness sets: Hinglish, romanized, ASR-noisy text"]),
          ("End to end", ["Task success rate and human evaluation", "Regression suites and release gates",
                          "Sample sizes and confidence intervals"])],
         [ARXIV + "2305.15386", ARXIV + "2408.11440"]),
    _mod("hv-launch", "process", "Launching and improving a new locale",
         "The step-by-step programme from scoping to post-launch, with the Bixby capsule details.",
         "https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl",
         [("Platform", ["Locale targets and per-locale resources in a capsule",
                        "Training utterances and Aligned NL per language", "Dialog localization for Hindi"]),
          ("Release", ["Dog-food and beta programmes", "Launch gates and staged rollout"]),
          ("Improve", ["Monitoring live quality", "Mining failures and active learning", "Retraining cadence"])]),
]
MODULE_BY_SLUG = {m["slug"]: m for m in MODULES}
SIDES = [
    {"id": "asr", "title": "ASR (speech to text)"},
    {"id": "nlu", "title": "NLU (text to meaning)"},
    {"id": "process", "title": "Data, testing and launch"},
]

# ------------------------------------------------------------------ models

def _model(name, org, kind, url, *, paper="", licence="", size="", on_device="", result="", notes="", top=False):
    return {"name": name, "org": org, "kind": kind, "url": url, "paper": paper, "licence": licence, "size": size,
            "on_device": on_device, "result": result, "notes": notes, "top_pick": top}


MODEL_KINDS = [
    {"id": "asr", "title": "Hindi ASR models"},
    {"id": "nlu", "title": "NLU encoders"},
    {"id": "llm", "title": "LLMs and translation"},
    {"id": "tooling", "title": "Text tools, TTS and runtimes"},
]

MODELS = [
    # ASR
    _model("IndicConformer 600M (multilingual)", "AI4Bharat", "asr",
           "https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual",
           licence="MIT (gated: accept terms)", size="600M", on_device="Server; community ONNX/CoreML ports exist",
           result="No official Hindi WER on the card; third-party numbers vary.",
           notes="Conformer, hybrid CTC + RNN-T, 22 Indian languages. Needs AI4Bharat's NeMo fork. The strongest "
                 "open base to fine-tune for Hindi.", top=True),
    _model("IndicWhisper (Vistaar)", "AI4Bharat", "asr", "https://github.com/AI4Bharat/vistaar",
           paper=ARXIV + "2305.15386", licence="MIT", size="Whisper fine-tune",
           on_device="Server",
           result="Hindi WER 13.6 average on Vistaar (Kathbath 10.3, FLEURS 11.4, Gramvaani 26.8); Google STT 23.9 "
                  "and Azure 20.0 on the same sets (2023).",
           notes="Whisper fine-tuned on 10.7K hours of public data in 12 Indian languages. Good offline baseline.", top=True),
    _model("IndicWav2Vec", "AI4Bharat", "asr", "https://github.com/AI4Bharat/IndicWav2Vec",
           paper=ARXIV + "2111.03945", licence="MIT", size="Large (~300M)", on_device="Server",
           result="Hindi WER 21.0 average on Vistaar (2023).",
           notes="wav2vec 2.0 pre-trained on 40 Indian languages. Good for studying SSL; newer models beat it."),
    _model("Whisper large-v3", "OpenAI", "asr", "https://huggingface.co/openai/whisper-large-v3",
           paper=ARXIV + "2212.04356", licence="Apache-2.0 (weights card)", size="1.55B",
           on_device="Too big; small/turbo variants for edge",
           notes="Strong multilingual baseline and the usual fine-tuning start. Watch for hallucination on silence "
                 "and for Hindi output in Urdu script."),
    _model("MMS-1B-all", "Meta", "asr", "https://huggingface.co/facebook/mms-1b-all", paper=ARXIV + "2305.13516",
           licence="CC-BY-NC-4.0 (non-commercial)", size="1B", on_device="Server",
           notes="1,000+ languages with per-language adapters. Research only: the licence blocks product use."),
    _model("SeamlessM4T v2", "Meta", "asr", "https://huggingface.co/facebook/seamless-m4t-v2-large",
           paper=ARXIV + "2308.11596", licence="CC-BY-NC-4.0 (non-commercial)", size="2.3B", on_device="Server",
           notes="Speech recognition and translation in one model; useful for research comparisons."),
    _model("Google Chirp (USM) on Cloud Speech-to-Text", "Google", "asr",
           "https://cloud.google.com/speech-to-text/v2/docs/chirp_3-model", paper=ARXIV + "2303.01037",
           licence="Commercial API", on_device="Cloud",
           notes="Google's Universal Speech Model family. A commercial baseline to compare against."),
    _model("Sarvam Saaras / Saarika", "Sarvam AI", "asr",
           "https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika", licence="Commercial API",
           on_device="Cloud",
           result="Saarika v2.5: Hindi WER 11.81, CER 4.42 on Vistaar (vendor-reported). Saarika is now legacy; "
                  "Sarvam recommends Saaras.",
           notes="Indian-language-first speech API with code-mixed support. A strong commercial Hindi baseline."),
    _model("Vosk Hindi models", "Alpha Cephei", "asr", "https://alphacephei.com/vosk/models",
           licence="Apache-2.0", size="Small model ~40 MB", on_device="Yes (Android, Raspberry Pi)",
           notes="Kaldi-based small offline model. Lower accuracy, but a handy on-device baseline and demo."),
    # NLU
    _model("MuRIL", "Google", "nlu", "https://huggingface.co/google/muril-base-cased", paper=ARXIV + "2103.10730",
           licence="Apache-2.0", size="236M (base)", on_device="Distil or quantise first",
           notes="Trained on 16 Indian languages and English, plus transliterated text, so it handles romanized Hindi. Often "
                 "best on NER.", top=True),
    _model("IndicBERT v2", "AI4Bharat", "nlu", "https://huggingface.co/ai4bharat/IndicBERTv2-MLM-only",
           paper=ARXIV + "2212.05409", licence="MIT", size="278M", on_device="Distil or quantise first",
           notes="23 Indic languages + English, evaluated on IndicXTREME. Strong default encoder for intent and "
                 "slot models.", top=True),
    _model("XLM-RoBERTa", "Meta", "nlu", "https://huggingface.co/FacebookAI/xlm-roberta-base", licence="MIT",
           size="270M (base)", on_device="Distil or quantise first",
           notes="The MASSIVE paper's baseline; good for cross-lingual transfer from English training data."),
    _model("LaBSE", "Google", "nlu", "https://huggingface.co/sentence-transformers/LaBSE", licence="Apache-2.0",
           size="471M", notes="Language-agnostic sentence embeddings: dedupe utterances, find near-duplicates "
                              "across languages, and build few-shot intent classifiers."),
    # LLM / MT
    _model("IndicTrans2", "AI4Bharat", "llm", "https://github.com/AI4Bharat/IndicTrans2", paper=ARXIV + "2305.16307",
           licence="MIT", size="1B (distilled 200M)",
           notes="English↔Hindi translation for translate-train: bootstrap Hindi NLU data from English utterances, "
                 "then fix with native speakers."),
    _model("Airavata", "AI4Bharat", "llm", "https://huggingface.co/ai4bharat/Airavata", paper=ARXIV + "2401.15006",
           licence="Llama 2 licence", size="7B",
           notes="Hindi instruction-tuned LLM. Useful for research on Hindi generation and labelling."),
    _model("Sarvam-1", "Sarvam AI", "llm", "https://huggingface.co/sarvamai/sarvam-1", licence="See model card",
           size="2B", notes="Small LLM trained for 10 Indian languages; a candidate for on-device Hindi tasks."),
    _model("IndicBART", "AI4Bharat", "llm", "https://huggingface.co/ai4bharat/IndicBART", licence="See model card",
           size="244M", notes="Seq2seq model for Indic generation tasks such as paraphrasing utterances."),
    # tooling
    _model("IndicXlit", "AI4Bharat", "tooling", "https://github.com/AI4Bharat/IndicXlit", paper=ARXIV + "2205.03018",
           licence="MIT", notes="Roman ↔ Devanagari transliteration; normalises Hinglish input for NLU.", top=True),
    _model("Indic NLP Library", "Anoop Kunchukuttan", "tooling",
           "https://github.com/anoopkunchukuttan/indic_nlp_library", licence="MIT",
           notes="Unicode normalisation, tokenisation and script conversion for Indic text."),
    _model("NeMo Text Processing (TN/ITN)", "NVIDIA", "tooling", "https://github.com/NVIDIA/NeMo-text-processing",
           licence="Apache-2.0",
           notes="WFST grammars for text normalisation and inverse normalisation, including Hindi."),
    _model("Indic Parler-TTS", "AI4Bharat", "tooling", "https://huggingface.co/ai4bharat/indic-parler-tts",
           licence="Apache-2.0 (gated)",
           notes="Hindi and other Indic TTS with controllable speaker style; use it to synthesise ASR training "
                 "audio for new commands."),
    _model("sherpa-onnx", "k2-fsa", "tooling", "https://github.com/k2-fsa/sherpa-onnx", licence="Apache-2.0",
           on_device="Yes (Android, iOS, embedded)",
           notes="Runs streaming ASR, wake word and VAD on device; good for prototyping on-device Hindi."),
    _model("jiwer", "Jitsi", "tooling", "https://github.com/jitsi/jiwer", licence="Apache-2.0",
           notes="WER/CER computation in Python. Normalise Hindi text first, or the numbers are wrong."),
]

# ------------------------------------------------------------------ datasets

def _ds(name, kind, url, *, paper="", licence="", size="", what="", use=""):
    return {"name": name, "kind": kind, "url": url, "paper": paper, "licence": licence, "size": size,
            "what": what, "use": use}


DATASET_KINDS = [
    {"id": "speech", "title": "Hindi speech (training)"},
    {"id": "benchmark", "title": "Speech test sets and benchmarks"},
    {"id": "nlu", "title": "Text and NLU"},
    {"id": "augment", "title": "Augmentation and synthesis"},
]

DATASETS = [
    _ds("IndicVoices", "speech", "https://huggingface.co/datasets/ai4bharat/IndicVoices", paper=ARXIV + "2403.01926",
        licence="CC-BY-4.0 (gated)", size="7,348 h from 16,237 speakers across 22 languages (paper)",
        what="Read (9%), extempore (74%) and conversational (17%) speech collected across India's districts.",
        use="The best natural, diverse Hindi training data available openly."),
    _ds("Kathbath", "speech", "https://huggingface.co/datasets/ai4bharat/Kathbath", paper=ARXIV + "2208.11761",
        licence="CC-BY-4.0 (gated)", size="~1,684 h across 12 languages",
        what="Read speech from many speakers, with a 'hard' noisy test split.", use="Training and testing."),
    _ds("Shrutilipi", "speech", "https://huggingface.co/datasets/ai4bharat/Shrutilipi", paper=ARXIV + "2208.12666",
        licence="CC-BY-4.0 (gated)", what="Audio-text pairs mined from All India Radio news bulletins.",
        use="Large volume of broadcast-style Hindi; less conversational."),
    _ds("Project Vaani", "speech", "https://huggingface.co/datasets/ARTPARK-IISc/Vaani", licence="CC-BY-4.0 (gated)",
        what="IISc/ARTPARK and Google programme recording speech across India's districts, describing images.",
        use="District-level accent coverage for Hindi belt states."),
    _ds("Mozilla Common Voice (Hindi)", "speech", "https://commonvoice.mozilla.org/en/datasets",
        paper=ARXIV + "1912.06670", licence="CC0", what="Crowd-sourced read sentences.",
        use="Small for Hindi, but CC0 and easy to use; a public test set."),
    _ds("MUCS 2021", "speech", "https://navana-tech.github.io/MUCS2021/", paper=ARXIV + "2104.00235",
        what="Challenge data for multilingual and Hindi-English code-switched ASR.",
        use="Train and test code-switched (Hinglish) recognition."),
    _ds("Gram Vaani ASR challenge", "speech", "https://sites.google.com/view/gramvaaniasrchallenge",
        what="Telephone-quality Hindi from rural community radio users.",
        use="The hardest Hindi test (8 kHz, noisy, regional)."),
    _ds("Vistaar benchmark", "benchmark", "https://github.com/AI4Bharat/vistaar", paper=ARXIV + "2305.15386",
        licence="MIT (code)", what="59 test sets across Indian languages; Hindi: Kathbath, FLEURS, Common Voice, "
                                   "IndicTTS, MUCS, Gramvaani.",
        use="The standard way to compare Hindi ASR models."),
    _ds("Lahaja", "benchmark", "https://huggingface.co/datasets/ai4bharat/Lahaja", paper=ARXIV + "2408.11440",
        licence="MIT (gated)", size="12.5 h, 132 speakers (122 non-native Hindi speakers)",
        what="Multi-accent Hindi benchmark.", use="Accent robustness test, especially non-native speakers."),
    _ds("FLEURS (hi_in)", "benchmark", "https://huggingface.co/datasets/google/fleurs", paper=ARXIV + "2205.12446",
        licence="CC-BY-4.0", what="Read Wikipedia sentences in 102 languages.", use="Cross-language comparison."),
    _ds("MASSIVE (hi-IN)", "nlu", "https://huggingface.co/datasets/AmazonScience/massive", paper=ARXIV + "2204.08582",
        licence="CC-BY-4.0", size="11,514 train / 2,033 dev / 2,974 test per locale",
        what="Virtual-assistant utterances with 60 intents and 55 slot types, localized by native speakers.",
        use="The closest public benchmark to a voice assistant's Hindi NLU."),
    _ds("Naamapadam", "nlu", "https://huggingface.co/datasets/ai4bharat/naamapadam", paper=ARXIV + "2212.10168",
        licence="CC0-1.0", what="Named-entity data (person, location, organization) for 11 Indic languages.",
        use="Train and test entity recognition."),
    _ds("IndicXNLI", "nlu", "https://huggingface.co/datasets/Divyanshu/indicxnli", licence="CC0-1.0",
        what="Natural language inference in Indic languages.", use="Pre-fine-tuning and zero-shot intent tricks."),
    _ds("Aksharantar", "nlu", "https://huggingface.co/datasets/ai4bharat/Aksharantar", paper=ARXIV + "2205.03018",
        licence="CC (see card)", what="Large Roman ↔ native-script transliteration pairs.",
        use="Train or test transliteration for romanized Hindi input."),
    _ds("IndicCorp v2 (via IndicBERT repo)", "nlu", "https://github.com/AI4Bharat/IndicBERT",
        paper=ARXIV + "2212.05409", what="Large monolingual Indic text corpus.",
        use="Language-model text for ASR decoding and domain adaptation."),
    _ds("MUSAN noise corpus", "augment", "https://www.openslr.org/17/", licence="CC-BY-4.0",
        what="Music, speech and noise recordings.", use="Mix in background noise for robust ASR."),
    _ds("Room impulse responses (OpenSLR 28)", "augment", "https://www.openslr.org/28/", licence="Apache-2.0",
        what="Real and simulated room impulse responses with noise.", use="Simulate far-field and reverberant rooms."),
    _ds("IndicTTS (IIT Madras)", "augment", "https://www.iitm.ac.in/donlab/indictts/",
        what="Studio TTS voices and data for Indian languages.", use="Synthetic Hindi speech; also a Vistaar test set."),
]

# ------------------------------------------------------------------ papers (all IDs checked on arXiv)

def _paper(arxiv_id, title, year, topic, why, top=False):
    return {"id": arxiv_id, "title": title, "year": year, "topic": topic, "url": ARXIV + arxiv_id, "why": why,
            "top_pick": top}


PAPER_TOPICS = [
    {"id": "indic-asr", "title": "Hindi and Indic ASR"},
    {"id": "asr-core", "title": "Core ASR methods"},
    {"id": "data", "title": "Data, benchmarks and augmentation"},
    {"id": "nlu", "title": "NLU and spoken language understanding"},
    {"id": "codemix", "title": "Code-mixing and transliteration"},
    {"id": "device", "title": "On-device, wake word and biasing"},
]

PAPERS = [
    _paper("2305.15386", "Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR", 2023, "indic-asr",
           "Introduces IndicWhisper and the benchmark everyone uses to compare Hindi ASR.", True),
    _paper("2111.03945", "Towards Building ASR Systems for the Next Billion Users", 2021, "indic-asr",
           "IndicWav2Vec: self-supervised pre-training on 40 Indian languages, then fine-tuning."),
    _paper("2403.01926", "IndicVoices: Towards building an Inclusive Multilingual Speech Dataset for Indian "
                         "Languages", 2024, "indic-asr",
           "How to design a diverse collection across districts, speakers and speaking styles: a template for "
           "your own data plan.", True),
    _paper("2408.11440", "LAHAJA: A Robust Multi-accent Benchmark for Evaluating Hindi ASR Systems", 2024,
           "indic-asr", "Shows how much Hindi ASR degrades on non-native and regional accents."),
    _paper("2208.11761", "IndicSUPERB: A Speech Processing Universal Performance Benchmark for Indian languages",
           2022, "indic-asr", "Releases Kathbath and benchmarks speech tasks beyond ASR."),
    _paper("2208.12666", "Effectiveness of Mining Audio and Text Pairs from Public Data for Improving ASR Systems "
                         "for Low-Resource Languages", 2022, "data",
           "Shrutilipi: mining radio news to build cheap training data."),
    _paper("2212.04356", "Robust Speech Recognition via Large-Scale Weak Supervision", 2022, "asr-core",
           "Whisper: why weakly supervised multilingual training generalises.", True),
    _paper("2005.08100", "Conformer: Convolution-augmented Transformer for Speech Recognition", 2020, "asr-core",
           "The encoder behind most production ASR, including IndicConformer.", True),
    _paper("2006.11477", "wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations", 2020,
           "asr-core", "Self-supervised speech: learn from unlabelled Hindi audio."),
    _paper("1211.3711", "Sequence Transduction with Recurrent Neural Networks", 2012, "asr-core",
           "The RNN-Transducer: the streaming model family voice assistants use."),
    _paper("2305.13516", "Scaling Speech Technology to 1,000+ Languages", 2023, "asr-core",
           "MMS: multilingual pre-training and per-language adapters for adding languages cheaply."),
    _paper("2303.01037", "Google USM: Scaling Automatic Speech Recognition Beyond 100 Languages", 2023, "asr-core",
           "How a large lab scales one model to many languages."),
    _paper("2308.11596", "SeamlessM4T: Massively Multilingual & Multimodal Machine Translation", 2023, "asr-core",
           "Joint speech recognition and translation."),
    _paper("1904.08779", "SpecAugment: A Simple Data Augmentation Method for Automatic Speech Recognition", 2019,
           "data", "The default augmentation for ASR training."),
    _paper("1909.11699", "Speech Recognition with Augmented Synthesized Speech", 2019, "data",
           "When TTS-generated audio helps ASR, and how to stop it hurting.", True),
    _paper("1912.06670", "Common Voice: A Massively-Multilingual Speech Corpus", 2019, "data",
           "How crowd-sourced read speech is collected and validated."),
    _paper("2205.12446", "FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech", 2022, "data",
           "A parallel multilingual benchmark including Hindi."),
    _paper("1611.00068", "RNN Approaches to Text Normalization: A Challenge", 2016, "data",
           "Why text normalization is hard, and where neural models make 'silly' errors."),
    _paper("2204.08582", "MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 "
                         "Typologically-Diverse Languages", 2022, "nlu",
           "Virtual-assistant intents and slots in hi-IN; a ready benchmark and localization method.", True),
    _paper("2008.09335", "MTOP: A Comprehensive Multilingual Task-Oriented Semantic Parsing Benchmark", 2020, "nlu",
           "Compositional assistant parses across languages (includes Hindi)."),
    _paper("1902.10909", "BERT for Joint Intent Classification and Slot Filling", 2019, "nlu",
           "The standard joint intent-slot architecture."),
    _paper("2011.13205", "SLURP: A Spoken Language Understanding Resource Package", 2020, "nlu",
           "Spoken commands to a home assistant; the English source MASSIVE was localized from."),
    _paper("1904.03670", "Speech Model Pre-training for End-to-End Spoken Language Understanding", 2019, "nlu",
           "Skipping text: going straight from speech to intent."),
    _paper("2103.10730", "MuRIL: Multilingual Representations for Indian Languages", 2021, "nlu",
           "Why transliterated training text matters for Indian users.", True),
    _paper("2212.05409", "Towards Leaving No Indic Language Behind: Building Monolingual Corpora, Benchmark and "
                         "Models for Indic Languages", 2022, "nlu", "IndicBERT v2, IndicCorp v2 and IndicXTREME."),
    _paper("2212.10168", "Naamapadam: A Large-Scale Named Entity Annotated Data for Indic Languages", 2022, "nlu",
           "Hindi NER data and models."),
    _paper("2305.16307", "IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 "
                         "Scheduled Indian Languages", 2023, "nlu",
           "Translate-train: turning English assistant data into Hindi."),
    _paper("2401.15006", "Airavata: Introducing Hindi Instruction-tuned LLM", 2024, "nlu",
           "Building and evaluating a Hindi instruction-following LLM."),
    _paper("2211.09536", "Towards Building Text-To-Speech Systems for the Next Billion Users", 2022, "nlu",
           "Indic TTS for responses and for synthetic training audio."),
    _paper("2104.00235", "Multilingual and code-switching ASR challenges for low resource Indian languages", 2021,
           "codemix", "MUCS 2021: Hindi-English code-switched recognition.", True),
    _paper("2004.12376", "GLUECoS: An Evaluation Benchmark for Code-Switched NLP", 2020, "codemix",
           "Benchmarks for Hindi-English code-mixed language understanding."),
    _paper("2205.03018", "Aksharantar: Open Indic-language Transliteration datasets and models for the Next "
                         "Billion Users", 2022, "codemix", "IndicXlit: romanized Hindi ↔ Devanagari."),
    _paper("1811.06621", "Streaming End-to-end Speech Recognition For Mobile Devices", 2018, "device",
           "How Google put RNN-T on phones: latency, size and quality trade-offs.", True),
    _paper("1808.02480", "Deep context: end-to-end contextual speech recognition", 2018, "device",
           "CLAS: biasing ASR towards contacts and app names."),
    _paper("1711.07128", "Hello Edge: Keyword Spotting on Microcontrollers", 2017, "device",
           "Small-footprint wake-word models."),
]

# ------------------------------------------------------------------ launch playbook

PLAYBOOK = [
    {"id": "scope", "title": "Scope the language and market",
     "goal": "Decide exactly what 'Hindi support' means for launch.",
     "steps": ["Pick the locale (hi-IN) and devices: phone, watch, TV, fridge, car",
               "List launch domains and intents, ranked by usage in other locales",
               "Decide what to do with Hinglish and romanized input (accept both is the usual answer)",
               "Set launch quality targets per domain (ASR WER, NLU accuracy, task success)",
               "Check legal: consent, DPDP Act 2023, dataset licences"],
     "outputs": ["Launch scope document", "Quality targets", "Domain priority list"],
     "owners": "Product, language lead, legal",
     "pitfalls": ["Treating Hindi as English with a different script",
                  "Ignoring code-mixing until user testing finds it"]},
    {"id": "language", "title": "Define the language resources",
     "goal": "One agreed way to write, pronounce and normalise Hindi across ASR, NLU and TTS.",
     "steps": ["Write the transcription convention (Devanagari spelling, nukta, English words, numbers, fillers)",
               "Choose the canonical Unicode form and a normaliser",
               "Build or adopt a G2P and pronunciation lexicon for names",
               "Write TN/ITN grammars: numbers, dates, times, currency, units",
               "Write NLU annotation guidelines with Hindi examples for every slot"],
     "outputs": ["Transcription guide", "Normaliser", "Lexicon", "TN/ITN grammar", "Annotation guide"],
     "owners": "Linguists, ASR and NLU engineers",
     "pitfalls": ["Two teams spelling the same word differently, which inflates WER and breaks slot matching"]},
    {"id": "data", "title": "Plan and get data",
     "goal": "Training and test data that covers the variability matrix.",
     "steps": ["Fill the variability matrix and set quotas per cell",
               "Inventory open data and check licences (IndicVoices, Kathbath, Shrutilipi, MASSIVE…)",
               "Commission collection from vendors or crowd for gaps: wake word, commands, far-field, regions",
               "Generate synthetic data: LLM utterances for NLU, TTS audio for new commands",
               "Hold out clean, never-trained-on test sets first"],
     "outputs": ["Data plan with quotas", "Training sets", "Frozen test sets"],
     "owners": "Data lead, vendors, annotators",
     "pitfalls": ["Test speakers leaking into training", "Only read speech, so real spontaneous commands fail"]},
    {"id": "asr", "title": "Build ASR",
     "goal": "A Hindi model that meets WER targets on device and server.",
     "steps": ["Benchmark baselines: IndicConformer, IndicWhisper, Whisper, commercial APIs",
               "Fine-tune the chosen base on Hindi data; add augmentation",
               "Train the wake word for Hindi speakers, tune false accepts and rejects",
               "Add the domain LM and contextual biasing for contacts and apps",
               "Optimise for streaming and on-device: quantise, measure latency"],
     "outputs": ["ASR model", "Wake-word model", "Biasing setup", "Benchmark report"],
     "owners": "ASR team",
     "pitfalls": ["Optimising average WER while entity accuracy stays poor"]},
    {"id": "nlu", "title": "Build NLU",
     "goal": "Intents and slots that understand Hindi, Hinglish and romanized text.",
     "steps": ["Create training utterances per intent: translate-train, native writers, LLM generation",
               "Fine-tune a multilingual encoder (IndicBERT v2 or MuRIL) for joint intent and slots",
               "Add transliteration and normalisation in front of NLU",
               "Localise entity resolution: Hindi number words, dates, contacts in both scripts",
               "Train on ASR output too, not only clean text"],
     "outputs": ["NLU model", "Entity resolvers", "NLU test report"],
     "owners": "NLU team",
     "pitfalls": ["Training only on clean Devanagari text that ASR never produces"]},
    {"id": "platform", "title": "Localise the assistant",
     "goal": "Every capsule and response works in Hindi.",
     "steps": ["Add the hi-IN locale to each capsule's targets",
               "Write training utterances (Aligned NL) per goal in Hindi",
               "Localise dialog and responses with gender and honorific agreement",
               "Pick and tune the Hindi TTS voice; check pronunciation of names and numbers",
               "Localise UI strings, help and error messages"],
     "outputs": ["Localised capsules", "Hindi dialog", "TTS voice"],
     "owners": "Capsule developers, content writers",
     "pitfalls": ["Literal translations of English responses that sound unnatural"]},
    {"id": "test", "title": "Test end to end",
     "goal": "Evidence the launch targets are met.",
     "steps": ["Run ASR tests per slice; run NLU tests on clean and ASR text",
               "Run end-to-end task tests on real devices in real rooms",
               "Human evaluation with native speakers from several regions",
               "Regression suite against other locales (no harm to English/Indian English)",
               "Fix, retrain, repeat until the gates pass"],
     "outputs": ["Test report per slice", "Go/no-go sign-off"],
     "owners": "QA, language lead",
     "pitfalls": ["Testing in quiet offices only"]},
    {"id": "beta", "title": "Dog-food and beta",
     "goal": "Real users, real devices, before public launch.",
     "steps": ["Internal dog-food with Hindi speakers from different regions",
               "Closed beta with opted-in users; collect consented failure samples",
               "Triage failures by type: ASR, NLU, entity, capsule, TTS",
               "Fix top issues and retrain"],
     "outputs": ["Beta findings", "Updated models"], "owners": "Programme, QA",
     "pitfalls": ["Beta testers who are all fluent English speakers"]},
    {"id": "launch", "title": "Launch",
     "goal": "Ship safely and be able to roll back.",
     "steps": ["Staged rollout by device and region", "Dashboards: usage, task success, fallbacks, latency",
               "Rollback plan and on-call"],
     "outputs": ["Live hi-IN locale"], "owners": "Programme, SRE", "pitfalls": ["No rollback path for models"]},
    {"id": "improve", "title": "Improve continuously",
     "goal": "Quality keeps rising after launch.",
     "steps": ["Mine low-confidence and failed requests (with consent)", "Label and add them to training",
               "Retrain on a regular cadence and re-run all test sets",
               "Add new intents and regional coverage based on usage"],
     "outputs": ["Monthly quality report", "Retrained models"], "owners": "ASR, NLU and data teams",
     "pitfalls": ["Retraining on live data without re-checking the frozen test sets"]},
]

# ------------------------------------------------------------------ testing

TESTING = [
    {"id": "asr", "title": "ASR testing", "metrics": [
        ("WER (word error rate)", "(substitutions + deletions + insertions) / reference words",
         "The main ASR metric. Normalise both sides first: Unicode, nukta, punctuation, numbers."),
        ("CER (character error rate)", "The same, over characters",
         "Fairer for Hindi, where one spelling variant counts as a whole-word error."),
        ("Entity / keyword error rate", "Errors on contact names, apps, numbers and command words only",
         "What actually breaks commands, even when WER looks fine."),
        ("Sentence error rate", "Share of utterances with any error", "Matches how users feel short commands."),
        ("Wake-word FAR / FRR", "False accepts per hour of non-wake audio; false rejects per wake attempt",
         "Tune per device and test with Hindi TV and background speech."),
        ("Latency and real-time factor", "Time to final result after end of speech; compute per second of audio",
         "Measure on the target device, not a server GPU."),
     ], "slices": ["Accent / region", "Gender and age group (including children and elderly)",
                   "Native vs non-native speakers", "Device and microphone", "Near vs far field",
                   "Noise type and SNR (TV, traffic, kitchen, car)", "Domain (alarms, calls, music…)",
                   "Code-mix level", "Utterance length"]},
    {"id": "nlu", "title": "NLU testing", "metrics": [
        ("Intent accuracy", "Share of utterances with the right intent", "Report per intent, not only overall."),
        ("Slot F1", "Precision and recall of slot spans and labels", "Use exact span match."),
        ("Exact match (semantic accuracy)", "Intent and all slots correct", "The NLU launch metric."),
        ("Robustness gap", "Score on clean text minus score on ASR output, Hinglish or romanized input",
         "Shows where NLU depends on perfect input."),
        ("Out-of-scope detection", "Correct rejection of requests the assistant can't do",
         "Avoid confidently wrong actions."),
     ], "slices": ["Devanagari vs romanized vs code-mixed", "Clean text vs ASR n-best",
                   "Paraphrase and word order variation", "Rare entities", "Per intent and domain"]},
    {"id": "e2e", "title": "End-to-end and human testing", "metrics": [
        ("Task success rate", "Did the device do what the user asked?", "The launch gate."),
        ("Turns to success / fallback rate", "Extra turns and 'sorry, I didn't get that' rate",
         "A measure of user friction."),
        ("Response quality (human rating)", "Native speakers rate correctness, naturalness, politeness",
         "Catches unnatural or wrongly gendered Hindi."),
        ("TTS intelligibility and MOS", "Listener scores of the Hindi voice", "Includes names and numbers."),
        ("Regression", "No drop in other locales or earlier Hindi builds", "Run before every release."),
     ], "slices": ["Real devices and rooms", "Regions", "First-time users vs experienced users"]},
]

TEST_SIZING = [
    "WER differences under about 0.5% absolute need thousands of utterances per slice to be meaningful; use "
    "bootstrap confidence intervals.",
    "Keep test speakers out of training data entirely (speaker-disjoint splits).",
    "Freeze test sets and version them; never tune on them.",
    "Have at least a few hundred utterances per important slice (accent, device, noise) so slice WER is stable.",
    "For NLU, aim for a few dozen test utterances per intent from people who did not write the training data.",
]

# ------------------------------------------------------------------ data variability, sourcing and generation

VARIABILITY = [
    {"dimension": "Speaker accent and region",
     "values": ["Western UP / Delhi (Khari Boli)", "Eastern UP / Bihar (Bhojpuri, Awadhi, Maithili influence)",
                "Rajasthan (Marwari influence)", "Madhya Pradesh / Chhattisgarh", "Haryana", "Uttarakhand / Himachal",
                "Non-native: Bengali, Marathi, Gujarati, Punjabi, Tamil, Telugu, Kannada, Malayalam speakers"],
     "why": "Hindi users span many first languages; Lahaja shows non-native accents are where ASR degrades.",
     "how": "District-level collection (IndicVoices, Vaani) plus vendor quotas per state."},
    {"dimension": "Speaker demographics", "values": ["Gender balance", "Children, adults, elderly",
                                                     "Education and literacy levels", "Urban vs rural"],
     "why": "Pitch, pace and vocabulary vary; rural and elderly users are often under-represented.",
     "how": "Quota per cell in collection; check the distribution of open datasets first."},
    {"dimension": "Speaking style", "values": ["Read prompts", "Spontaneous commands", "Conversational follow-ups",
                                               "Disfluencies (umm, अच्छा, restarts)", "Fast vs slow speech"],
     "why": "Read speech is cheap but users don't read to assistants.",
     "how": "Use scenario prompts ('ask the phone to…') instead of sentences to read."},
    {"dimension": "Language mixing", "values": ["Pure Hindi", "Hinglish with English nouns (alarm, Wi-Fi)",
                                                "Heavy mixing with English verbs", "Urdu-origin vs Sanskritised words"],
     "why": "Most Indian users mix; NLU and ASR must agree on how mixed words are written.",
     "how": "Collect naturally, label mix level, and generate Hinglish variants with an LLM."},
    {"dimension": "Script (for NLU and typed input)", "values": ["Devanagari", "Romanized Hindi", "Mixed script"],
     "why": "Typed and keyboard input is often romanized; ASR output depends on your convention.",
     "how": "Transliteration (IndicXlit) plus LLM generation in each script."},
    {"dimension": "Acoustic environment", "values": ["Quiet room", "TV or music in background", "Traffic / outdoors",
                                                     "Kitchen, fan, AC", "In-car", "Crowds and other speakers"],
     "why": "Indian homes are often noisy and multi-speaker.",
     "how": "Record in real places, and augment with MUSAN noise at several SNRs."},
    {"dimension": "Device and distance", "values": ["Phone near-field", "Phone at arm's length", "Watch",
                                                    "TV / fridge far-field", "Earbuds", "Low-end mics"],
     "why": "Microphones and distance change the signal more than accent does.",
     "how": "Collect on the target hardware; simulate distance with room impulse responses."},
    {"dimension": "Content and entities", "values": ["Contacts (Indian names in both scripts)", "App names",
                                                     "Places and addresses", "Numbers, dates, times, money",
                                                     "Song and film titles", "Every launch intent"],
     "why": "Entities are where commands fail.",
     "how": "Template + gazetteer generation, TTS for rare names, and biasing tests."},
]

SOURCING = [
    {"method": "Open datasets", "how": "IndicVoices, Kathbath, Shrutilipi, Vaani, Common Voice, MASSIVE, "
                                      "Naamapadam (see the Datasets list).",
     "pros": "Free and fast; big and diverse.", "cons": "Licences vary (watch non-commercial); not your domain or "
                                                        "devices; often read speech."},
    {"method": "Vendor collection", "how": "Commission recordings with speaker, device, environment and script "
                                          "quotas; a specification with prompts and QA rules.",
     "pros": "Matches your devices, domains and quotas.", "cons": "Costly and slow; needs strong QA."},
    {"method": "Crowd / community collection", "how": "Platforms such as Karya pay rural workers fairly to record "
                                                     "and transcribe; good for regional reach.",
     "pros": "Reach rural and regional speakers.", "cons": "Variable quality; needs validation passes."},
    {"method": "In-house dog-food", "how": "Employees and testers record commands on real devices.",
     "pros": "Realistic usage, quick.", "cons": "Biased to urban, educated speakers."},
    {"method": "Live traffic (with consent)", "how": "After launch, sample opted-in requests, mainly failures and "
                                                    "low-confidence ones, then label them.",
     "pros": "Exactly your distribution.", "cons": "Only after launch; strict privacy controls needed."},
    {"method": "Mining public audio", "how": "Align broadcast audio with text (as Shrutilipi did with radio news).",
     "pros": "Large volume cheaply.", "cons": "Broadcast style; check rights."},
]

GENERATION = [
    {"name": "LLM utterance generation (NLU)", "for": "nlu",
     "how": "Give the LLM an intent, slot list and example values; ask for varied phrasings in Devanagari, "
            "romanized and Hinglish, with slot labels. Then dedupe, validate slots and have native speakers review "
            "a sample.",
     "caution": "LLMs repeat patterns and write formal Hindi; ask for colloquial variants and check diversity.",
     "tool": "The Utterance generator on this page does this."},
    {"name": "Template + gazetteer expansion (NLU)", "for": "nlu",
     "how": "Carrier phrases with slots ('{contact} को फोन करो') filled from entity lists of names, apps, times.",
     "caution": "Too many templated sentences make models brittle; mix with natural data.", "tool": ""},
    {"name": "Translate-train (NLU)", "for": "nlu",
     "how": "Translate English training utterances with IndicTrans2, project slot spans, then fix with linguists.",
     "caution": "Translations sound unnatural and miss Hinglish; use as a bootstrap only.", "tool": "IndicTrans2"},
    {"name": "TTS synthetic speech (ASR)", "for": "asr",
     "how": "Synthesise new commands and rare entity names with several Hindi TTS voices and styles, then add "
            "noise and reverberation.",
     "caution": "Too much synthetic audio hurts real-speech WER; keep it a minority and check on real test sets.",
     "tool": "Indic Parler-TTS, IndicTTS"},
    {"name": "Noise and room augmentation (ASR)", "for": "asr",
     "how": "Mix MUSAN noise at several SNRs and convolve with room impulse responses to simulate far-field.",
     "caution": "Match the noise types your users actually have.", "tool": "MUSAN, OpenSLR RIRs"},
    {"name": "Speed / pitch perturbation and SpecAugment (ASR)", "for": "asr",
     "how": "Speed perturb at 0.9x/1.0x/1.1x; mask time and frequency bands during training.",
     "caution": "Standard and safe; small gains.", "tool": "SpecAugment, torchaudio"},
    {"name": "Pseudo-labelling unlabelled audio (ASR)", "for": "asr",
     "how": "Transcribe large unlabelled Hindi audio with a strong model, keep high-confidence results, train on "
            "them.",
     "caution": "Errors reinforce themselves; filter by confidence and agreement between models.", "tool": ""},
]

PLATFORM_NOTES = [
    "Each Bixby capsule declares the device types and language/locale pairs it supports in the targets block of "
    "capsule.bxb, so adding Hindi means adding hi-IN targets to every capsule you launch.",
    "Natural language training is per language: each capsule needs Hindi training utterances, written as Aligned NL "
    "(the utterance plus its goal and slot annotations).",
    "Training entries can also be used as tests: a mismatch means the planner's goal differs from the one in the "
    "Aligned NL.",
    "Dialog and responses are localized per locale; Hindi needs gender and case agreement in templates.",
    "Public sources disagree on whether Bixby supports Hindi in every market today; this tab covers adding or "
    "improving any locale, based on public documentation only.",
]
