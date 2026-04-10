# -*- coding: utf-8 -*-
import os
import base64
import json
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
import cgi
import tempfile

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:31b-cloud"
PORT = 8899

HTML_PAGE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Image Describer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        body[dir="rtl"] { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }
        h1 {
            margin-top: 40px;
            font-size: 2rem;
            background: linear-gradient(135deg, #a78bfa, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #666; margin-top: 8px; font-size: 0.9rem; }
        .lang-bar {
            margin-top: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .lang-bar label { color: #888; font-size: 0.9rem; }
        .lang-bar select {
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid #333;
            background: #111128;
            color: #e0e0e0;
            font-size: 0.95rem;
            outline: none;
            cursor: pointer;
        }
        .lang-bar select:focus { border-color: #6366f1; }
        .container {
            width: 100%;
            max-width: 900px;
            padding: 20px;
            margin-top: 16px;
        }
        .upload-area {
            border: 2px dashed #333;
            border-radius: 16px;
            padding: 60px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #111128;
        }
        .upload-area:hover, .upload-area.dragover {
            border-color: #6366f1;
            background: #15153a;
        }
        .upload-area svg { width: 64px; height: 64px; fill: #6366f1; margin-bottom: 16px; }
        .upload-area p { color: #888; margin-top: 8px; }
        .upload-area .formats { font-size: 0.8rem; color: #555; margin-top: 12px; }
        #fileInput { display: none; }

        .preview-section {
            display: none;
            margin-top: 24px;
            border-radius: 16px;
            overflow: hidden;
            background: #111128;
            border: 1px solid #222;
        }
        .preview-section.active { display: block; }
        .preview-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid #222;
        }
        .preview-header .filename { font-weight: 600; color: #a78bfa; }
        .preview-header .filesize { color: #666; font-size: 0.85rem; }
        .preview-img-wrap {
            display: flex;
            justify-content: center;
            padding: 20px;
            background: #0d0d20;
        }
        .preview-img-wrap img {
            max-width: 100%;
            max-height: 400px;
            border-radius: 8px;
        }

        .prompt-row {
            display: none;
            margin-top: 16px;
            gap: 12px;
        }
        .prompt-row.active { display: flex; }
        .prompt-row input {
            flex: 1;
            padding: 14px 18px;
            border-radius: 12px;
            border: 1px solid #222;
            background: #111128;
            color: #e0e0e0;
            font-size: 1rem;
            outline: none;
        }
        .prompt-row input:focus { border-color: #6366f1; }
        .prompt-row input::placeholder { color: #555; }
        .btn {
            padding: 14px 28px;
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, #6366f1, #a78bfa);
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            white-space: nowrap;
        }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .result-section {
            display: none;
            margin-top: 24px;
            padding: 24px;
            background: #111128;
            border: 1px solid #222;
            border-radius: 16px;
        }
        .result-section.active { display: block; }
        .result-section h3 {
            color: #a78bfa;
            margin-bottom: 12px;
            font-size: 1rem;
        }
        .result-text {
            line-height: 1.7;
            color: #ccc;
            white-space: pre-wrap;
        }

        .loading {
            display: none;
            margin-top: 24px;
            text-align: center;
            padding: 40px;
        }
        .loading.active { display: block; }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid #222;
            border-top-color: #6366f1;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading p { color: #888; }

        .new-btn {
            display: none;
            margin-top: 16px;
            text-align: center;
        }
        .new-btn.active { display: block; }
        .btn-outline {
            padding: 12px 24px;
            border-radius: 12px;
            border: 1px solid #333;
            background: transparent;
            color: #a78bfa;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-outline:hover { border-color: #6366f1; background: #15153a; }
    </style>
</head>
<body>
    <h1 id="title">AI Image Describer</h1>
    <p class="subtitle" id="subtitle">Upload an image and let Gemma 4 describe it</p>

    <div class="lang-bar">
        <label id="langLabel">Language:</label>
        <select id="langSelect" onchange="switchLang()">
            <option value="en">English</option>
            <option value="ar">العربية</option>
            <option value="fr">Francais</option>
            <option value="es">Espanol</option>
            <option value="de">Deutsch</option>
            <option value="it">Italiano</option>
            <option value="pt">Portugues</option>
            <option value="ru">Русский</option>
            <option value="zh">中文</option>
            <option value="ja">日本語</option>
            <option value="ko">한국어</option>
            <option value="hi">हिन्दी</option>
            <option value="tr">Turkce</option>
            <option value="nl">Nederlands</option>
            <option value="pl">Polski</option>
            <option value="sv">Svenska</option>
            <option value="uk">Українська</option>
            <option value="vi">Tieng Viet</option>
            <option value="th">ไทย</option>
            <option value="id">Bahasa Indonesia</option>
            <option value="ms">Bahasa Melayu</option>
            <option value="fa">فارسی</option>
            <option value="he">עברית</option>
            <option value="ur">اردو</option>
            <option value="bn">বাংলা</option>
            <option value="ta">தமிழ்</option>
            <option value="te">తెలుగు</option>
            <option value="sw">Kiswahili</option>
            <option value="ro">Romana</option>
            <option value="el">Ελληνικά</option>
            <option value="hu">Magyar</option>
            <option value="cs">Cestina</option>
            <option value="da">Dansk</option>
            <option value="fi">Suomi</option>
            <option value="no">Norsk</option>
        </select>
    </div>

    <div class="container">
        <div class="upload-area" id="uploadArea">
            <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <p id="uploadText">Drop an image here or click to upload</p>
            <p class="formats" id="formatsText">Supports JPG, PNG, GIF, WebP, BMP</p>
            <input type="file" id="fileInput" accept="image/*">
        </div>

        <div class="preview-section" id="previewSection">
            <div class="preview-header">
                <span class="filename" id="fileName"></span>
                <span class="filesize" id="fileSize"></span>
            </div>
            <div class="preview-img-wrap">
                <img id="previewImg" src="" alt="Preview">
            </div>
        </div>

        <div class="prompt-row" id="promptRow">
            <input type="text" id="promptInput" placeholder="Describe this image in detail (or type your own prompt)">
            <button class="btn" id="describeBtn" onclick="describeImage()">Describe</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p id="loadingText">Gemma 4 is analyzing the image...</p>
        </div>

        <div class="result-section" id="resultSection">
            <h3 id="resultTitle">Description</h3>
            <div class="result-text" id="resultText"></div>
        </div>

        <div class="new-btn" id="newBtn">
            <button class="btn-outline" onclick="resetAll()" id="newBtnText">Describe another image</button>
        </div>
    </div>

    <script>
        const RTL_LANGS = new Set(['ar', 'fa', 'he', 'ur']);

        const TRANSLATIONS = {
            en: { title: "AI Image Describer", subtitle: "Upload an image and let Gemma 4 describe it", langLabel: "Language:", upload: "Drop an image here or click to upload", formats: "Supports JPG, PNG, GIF, WebP, BMP", placeholder: "Describe this image in detail (or type your own prompt)", btn: "Describe", loading: "Gemma 4 is analyzing the image...", result: "Description", another: "Describe another image", promptPrefix: "Describe this image in detail." },
            ar: { title: "واصف الصور بالذكاء الاصطناعي", subtitle: "ارفع صورة ودع Gemma 4 يصفها", langLabel: "اللغة:", upload: "اسحب صورة هنا او اضغط للرفع", formats: "يدعم JPG, PNG, GIF, WebP, BMP", placeholder: "صف هذه الصورة بالتفصيل (او اكتب طلبك)", btn: "وصف", loading: "...Gemma 4 يحلل الصورة", result: "الوصف", another: "وصف صورة اخرى", promptPrefix: "صف هذه الصورة بالتفصيل. اجب بالعربية فقط." },
            fr: { title: "Descripteur d'Images IA", subtitle: "Telechargez une image et laissez Gemma 4 la decrire", langLabel: "Langue :", upload: "Glissez une image ici ou cliquez pour telecharger", formats: "Supporte JPG, PNG, GIF, WebP, BMP", placeholder: "Decrivez cette image en detail (ou tapez votre propre requete)", btn: "Decrire", loading: "Gemma 4 analyse l'image...", result: "Description", another: "Decrire une autre image", promptPrefix: "Decris cette image en detail. Reponds en francais uniquement." },
            es: { title: "Descriptor de Imagenes IA", subtitle: "Sube una imagen y deja que Gemma 4 la describa", langLabel: "Idioma:", upload: "Arrastra una imagen aqui o haz clic para subir", formats: "Soporta JPG, PNG, GIF, WebP, BMP", placeholder: "Describe esta imagen en detalle (o escribe tu propio prompt)", btn: "Describir", loading: "Gemma 4 esta analizando la imagen...", result: "Descripcion", another: "Describir otra imagen", promptPrefix: "Describe esta imagen en detalle. Responde solo en espanol." },
            de: { title: "KI-Bildbeschreiber", subtitle: "Laden Sie ein Bild hoch und lassen Sie Gemma 4 es beschreiben", langLabel: "Sprache:", upload: "Bild hierher ziehen oder klicken zum Hochladen", formats: "Unterstutzt JPG, PNG, GIF, WebP, BMP", placeholder: "Beschreibe dieses Bild im Detail (oder eigene Eingabe)", btn: "Beschreiben", loading: "Gemma 4 analysiert das Bild...", result: "Beschreibung", another: "Ein weiteres Bild beschreiben", promptPrefix: "Beschreibe dieses Bild im Detail. Antworte nur auf Deutsch." },
            it: { title: "Descrittore di Immagini IA", subtitle: "Carica un'immagine e lascia che Gemma 4 la descriva", langLabel: "Lingua:", upload: "Trascina un'immagine qui o clicca per caricare", formats: "Supporta JPG, PNG, GIF, WebP, BMP", placeholder: "Descrivi questa immagine in dettaglio (o scrivi il tuo prompt)", btn: "Descrivi", loading: "Gemma 4 sta analizzando l'immagine...", result: "Descrizione", another: "Descrivi un'altra immagine", promptPrefix: "Descrivi questa immagine in dettaglio. Rispondi solo in italiano." },
            pt: { title: "Descritor de Imagens IA", subtitle: "Carregue uma imagem e deixe o Gemma 4 descreve-la", langLabel: "Idioma:", upload: "Arraste uma imagem aqui ou clique para carregar", formats: "Suporta JPG, PNG, GIF, WebP, BMP", placeholder: "Descreva esta imagem em detalhe (ou digite seu proprio prompt)", btn: "Descrever", loading: "Gemma 4 esta analisando a imagem...", result: "Descricao", another: "Descrever outra imagem", promptPrefix: "Descreva esta imagem em detalhe. Responda apenas em portugues." },
            ru: { title: "ИИ Описание Изображений", subtitle: "Загрузите изображение и Gemma 4 опишет его", langLabel: "Язык:", upload: "Перетащите изображение сюда или нажмите для загрузки", formats: "Поддерживает JPG, PNG, GIF, WebP, BMP", placeholder: "Опишите это изображение подробно (или введите свой запрос)", btn: "Описать", loading: "Gemma 4 анализирует изображение...", result: "Описание", another: "Описать другое изображение", promptPrefix: "Опиши это изображение подробно. Отвечай только на русском языке." },
            zh: { title: "AI 图像描述器", subtitle: "上传图片，让 Gemma 4 为你描述", langLabel: "语言：", upload: "拖放图片到此处或点击上传", formats: "支持 JPG, PNG, GIF, WebP, BMP", placeholder: "详细描述这张图片（或输入你的提示）", btn: "描述", loading: "Gemma 4 正在分析图片...", result: "描述结果", another: "描述另一张图片", promptPrefix: "请详细描述这张图片。请只用中文回答。" },
            ja: { title: "AI 画像説明ツール", subtitle: "画像をアップロードして Gemma 4 に説明させましょう", langLabel: "言語：", upload: "画像をここにドロップまたはクリックしてアップロード", formats: "JPG, PNG, GIF, WebP, BMP に対応", placeholder: "この画像を詳しく説明してください（または独自のプロンプトを入力）", btn: "説明する", loading: "Gemma 4 が画像を分析中...", result: "説明", another: "別の画像を説明する", promptPrefix: "この画像を詳しく説明してください。日本語のみで回答してください。" },
            ko: { title: "AI 이미지 설명기", subtitle: "이미지를 업로드하면 Gemma 4가 설명해 드립니다", langLabel: "언어:", upload: "이미지를 여기에 드롭하거나 클릭하여 업로드", formats: "JPG, PNG, GIF, WebP, BMP 지원", placeholder: "이 이미지를 자세히 설명하세요 (또는 직접 프롬프트 입력)", btn: "설명하기", loading: "Gemma 4가 이미지를 분석 중...", result: "설명", another: "다른 이미지 설명하기", promptPrefix: "이 이미지를 자세히 설명하세요. 한국어로만 답변하세요." },
            hi: { title: "AI छवि वर्णनकर्ता", subtitle: "एक छवि अपलोड करें और Gemma 4 को इसका वर्णन करने दें", langLabel: "भाषा:", upload: "यहां एक छवि ड्रॉप करें या अपलोड करने के लिए क्लिक करें", formats: "JPG, PNG, GIF, WebP, BMP समर्थित", placeholder: "इस छवि का विस्तार से वर्णन करें (या अपना प्रॉम्प्ट लिखें)", btn: "वर्णन करें", loading: "Gemma 4 छवि का विश्लेषण कर रहा है...", result: "वर्णन", another: "एक और छवि का वर्णन करें", promptPrefix: "इस छवि का विस्तार से वर्णन करें। केवल हिंदी में उत्तर दें।" },
            tr: { title: "AI Gorsel Tanimlayici", subtitle: "Bir gorsel yukleyin ve Gemma 4'un tanimlamasini izleyin", langLabel: "Dil:", upload: "Gorseli buraya birakin veya yuklemek icin tiklayin", formats: "JPG, PNG, GIF, WebP, BMP desteklenir", placeholder: "Bu gorseli ayrintili olarak tanimlayin (veya kendi komutunuzu yazin)", btn: "Tanimla", loading: "Gemma 4 gorseli analiz ediyor...", result: "Tanim", another: "Baska bir gorsel tanimla", promptPrefix: "Bu gorseli ayrintili olarak tanimla. Sadece Turkce olarak yanit ver." },
            nl: { title: "AI Beeldbeschrijver", subtitle: "Upload een afbeelding en laat Gemma 4 het beschrijven", langLabel: "Taal:", upload: "Sleep een afbeelding hierheen of klik om te uploaden", formats: "Ondersteunt JPG, PNG, GIF, WebP, BMP", placeholder: "Beschrijf deze afbeelding in detail (of typ je eigen prompt)", btn: "Beschrijf", loading: "Gemma 4 analyseert de afbeelding...", result: "Beschrijving", another: "Beschrijf een andere afbeelding", promptPrefix: "Beschrijf deze afbeelding in detail. Antwoord alleen in het Nederlands." },
            pl: { title: "AI Opis Obrazow", subtitle: "Przeslij obraz i pozwol Gemma 4 go opisac", langLabel: "Jezyk:", upload: "Upusc obraz tutaj lub kliknij, aby przeslac", formats: "Obsluguje JPG, PNG, GIF, WebP, BMP", placeholder: "Opisz ten obraz szczegolowo (lub wpisz wlasne polecenie)", btn: "Opisz", loading: "Gemma 4 analizuje obraz...", result: "Opis", another: "Opisz inny obraz", promptPrefix: "Opisz ten obraz szczegolowo. Odpowiadaj tylko po polsku." },
            sv: { title: "AI Bildbeskrivare", subtitle: "Ladda upp en bild och lat Gemma 4 beskriva den", langLabel: "Sprak:", upload: "Slapp en bild har eller klicka for att ladda upp", formats: "Stoder JPG, PNG, GIF, WebP, BMP", placeholder: "Beskriv denna bild i detalj (eller skriv din egen prompt)", btn: "Beskriv", loading: "Gemma 4 analyserar bilden...", result: "Beskrivning", another: "Beskriv en annan bild", promptPrefix: "Beskriv denna bild i detalj. Svara bara pa svenska." },
            uk: { title: "AI Опис Зображень", subtitle: "Завантажте зображення i Gemma 4 опише його", langLabel: "Мова:", upload: "Перетягніть зображення сюди або натисніть для завантаження", formats: "Підтримує JPG, PNG, GIF, WebP, BMP", placeholder: "Опишіть це зображення детально (або введіть свій запит)", btn: "Описати", loading: "Gemma 4 аналізує зображення...", result: "Опис", another: "Описати інше зображення", promptPrefix: "Опиши це зображення детально. Відповідай тільки українською мовою." },
            vi: { title: "AI Mo Ta Hinh Anh", subtitle: "Tai anh len va de Gemma 4 mo ta", langLabel: "Ngon ngu:", upload: "Keo tha hinh anh vao day hoac nhan de tai len", formats: "Ho tro JPG, PNG, GIF, WebP, BMP", placeholder: "Mo ta hinh anh nay chi tiet (hoac nhap yeu cau cua ban)", btn: "Mo ta", loading: "Gemma 4 dang phan tich hinh anh...", result: "Mo ta", another: "Mo ta hinh anh khac", promptPrefix: "Mo ta hinh anh nay chi tiet. Chi tra loi bang tieng Viet." },
            th: { title: "AI อธิบายรูปภาพ", subtitle: "อัปโหลดรูปภาพแล้วให้ Gemma 4 อธิบาย", langLabel: "ภาษา:", upload: "ลากรูปภาพมาวางที่นี่หรือคลิกเพื่ออัปโหลด", formats: "รองรับ JPG, PNG, GIF, WebP, BMP", placeholder: "อธิบายรูปภาพนี้อย่างละเอียด (หรือพิมพ์คำสั่งของคุณ)", btn: "อธิบาย", loading: "Gemma 4 กำลังวิเคราะห์รูปภาพ...", result: "คำอธิบาย", another: "อธิบายรูปภาพอื่น", promptPrefix: "อธิบายรูปภาพนี้อย่างละเอียด ตอบเป็นภาษาไทยเท่านั้น" },
            id: { title: "AI Deskripsi Gambar", subtitle: "Unggah gambar dan biarkan Gemma 4 mendeskripsikannya", langLabel: "Bahasa:", upload: "Seret gambar ke sini atau klik untuk mengunggah", formats: "Mendukung JPG, PNG, GIF, WebP, BMP", placeholder: "Deskripsikan gambar ini secara detail (atau ketik perintah Anda)", btn: "Deskripsikan", loading: "Gemma 4 sedang menganalisis gambar...", result: "Deskripsi", another: "Deskripsikan gambar lain", promptPrefix: "Deskripsikan gambar ini secara detail. Jawab hanya dalam Bahasa Indonesia." },
            ms: { title: "AI Penerangan Imej", subtitle: "Muat naik imej dan biarkan Gemma 4 menerangkannya", langLabel: "Bahasa:", upload: "Seret imej ke sini atau klik untuk muat naik", formats: "Menyokong JPG, PNG, GIF, WebP, BMP", placeholder: "Terangkan imej ini secara terperinci (atau taip arahan anda)", btn: "Terangkan", loading: "Gemma 4 sedang menganalisis imej...", result: "Penerangan", another: "Terangkan imej lain", promptPrefix: "Terangkan imej ini secara terperinci. Jawab hanya dalam Bahasa Melayu." },
            fa: { title: "توصیف تصویر با هوش مصنوعی", subtitle: "یک تصویر بارگذاری کنید و بگذارید Gemma 4 آن را توصیف کند", langLabel: "زبان:", upload: "تصویر را اینجا رها کنید یا برای بارگذاری کلیک کنید", formats: "JPG, PNG, GIF, WebP, BMP پشتیبانی می‌شود", placeholder: "این تصویر را با جزئیات توصیف کنید (یا درخواست خود را بنویسید)", btn: "توصیف", loading: "...Gemma 4 در حال تحلیل تصویر است", result: "توصیف", another: "توصیف تصویر دیگر", promptPrefix: "این تصویر را با جزئیات توصیف کن. فقط به فارسی پاسخ بده." },
            he: { title: "תיאור תמונות בינה מלאכותית", subtitle: "העלו תמונה ותנו ל-Gemma 4 לתאר אותה", langLabel: "שפה:", upload: "גררו תמונה לכאן או לחצו להעלאה", formats: "תומך ב-JPG, PNG, GIF, WebP, BMP", placeholder: "תארו את התמונה הזו בפירוט (או הקלידו בקשה משלכם)", btn: "תאר", loading: "...Gemma 4 מנתח את התמונה", result: "תיאור", another: "תאר תמונה נוספת", promptPrefix: "תאר את התמונה הזו בפירוט. ענה בעברית בלבד." },
            ur: { title: "اے آئی تصویر بیان کنندہ", subtitle: "ایک تصویر اپلوڈ کریں اور Gemma 4 کو اسے بیان کرنے دیں", langLabel: "زبان:", upload: "تصویر یہاں چھوڑیں یا اپلوڈ کرنے کے لیے کلک کریں", formats: "JPG, PNG, GIF, WebP, BMP سپورٹ کرتا ہے", placeholder: "اس تصویر کو تفصیل سے بیان کریں (یا اپنا پرامپٹ لکھیں)", btn: "بیان کریں", loading: "...Gemma 4 تصویر کا تجزیہ کر رہا ہے", result: "بیان", another: "ایک اور تصویر بیان کریں", promptPrefix: "اس تصویر کو تفصیل سے بیان کریں۔ صرف اردو میں جواب دیں۔" },
            bn: { title: "AI ছবি বর্ণনাকারী", subtitle: "একটি ছবি আপলোড করুন এবং Gemma 4 কে বর্ণনা করতে দিন", langLabel: "ভাষা:", upload: "এখানে একটি ছবি ড্রপ করুন বা আপলোড করতে ক্লিক করুন", formats: "JPG, PNG, GIF, WebP, BMP সমর্থিত", placeholder: "এই ছবিটি বিস্তারিতভাবে বর্ণনা করুন (বা আপনার নিজের প্রম্পট লিখুন)", btn: "বর্ণনা করুন", loading: "Gemma 4 ছবি বিশ্লেষণ করছে...", result: "বর্ণনা", another: "আরেকটি ছবি বর্ণনা করুন", promptPrefix: "এই ছবিটি বিস্তারিতভাবে বর্ণনা করুন। শুধুমাত্র বাংলায় উত্তর দিন।" },
            ta: { title: "AI பட விவரிப்பான்", subtitle: "ஒரு படத்தை பதிவேற்றி Gemma 4 விவரிக்கட்டும்", langLabel: "மொழி:", upload: "இங்கே ஒரு படத்தை இழுக்கவும் அல்லது பதிவேற்ற கிளிக் செய்யவும்", formats: "JPG, PNG, GIF, WebP, BMP ஆதரிக்கப்படுகிறது", placeholder: "இந்தப் படத்தை விரிவாக விவரிக்கவும் (அல்லது உங்கள் சொந்த கட்டளையை தட்டச்சு செய்யவும்)", btn: "விவரி", loading: "Gemma 4 படத்தை பகுப்பாய்வு செய்கிறது...", result: "விவரிப்பு", another: "மற்றொரு படத்தை விவரி", promptPrefix: "இந்தப் படத்தை விரிவாக விவரிக்கவும். தமிழில் மட்டும் பதிலளிக்கவும்." },
            te: { title: "AI చిత్ర వర్ణనకర్త", subtitle: "చిత్రాన్ని అప్‌లోడ్ చేసి Gemma 4 వర్ణించనివ్వండి", langLabel: "భాష:", upload: "ఇక్కడ చిత్రాన్ని డ్రాప్ చేయండి లేదా అప్‌లోడ్ చేయడానికి క్లిక్ చేయండి", formats: "JPG, PNG, GIF, WebP, BMP మద్దతు", placeholder: "ఈ చిత్రాన్ని వివరంగా వర్ణించండి (లేదా మీ స్వంత ప్రాంప్ట్ టైప్ చేయండి)", btn: "వర్ణించు", loading: "Gemma 4 చిత్రాన్ని విశ్లేషిస్తోంది...", result: "వర్ణన", another: "మరో చిత్రాన్ని వర్ణించు", promptPrefix: "ఈ చిత్రాన్ని వివరంగా వర్ణించండి. తెలుగులో మాత్రమే సమాధానం ఇవ్వండి." },
            sw: { title: "AI Maelezo ya Picha", subtitle: "Pakia picha na uache Gemma 4 ieleze", langLabel: "Lugha:", upload: "Buruta picha hapa au bonyeza kupakia", formats: "Inasaidia JPG, PNG, GIF, WebP, BMP", placeholder: "Eleza picha hii kwa undani (au andika ombi lako)", btn: "Eleza", loading: "Gemma 4 inachambua picha...", result: "Maelezo", another: "Eleza picha nyingine", promptPrefix: "Eleza picha hii kwa undani. Jibu kwa Kiswahili pekee." },
            ro: { title: "AI Descriere Imagini", subtitle: "Incarcati o imagine si lasati Gemma 4 sa o descrie", langLabel: "Limba:", upload: "Trageti o imagine aici sau faceti clic pentru a incarca", formats: "Suporta JPG, PNG, GIF, WebP, BMP", placeholder: "Descrieti aceasta imagine in detaliu (sau scrieti propriul prompt)", btn: "Descrie", loading: "Gemma 4 analizeaza imaginea...", result: "Descriere", another: "Descrie alta imagine", promptPrefix: "Descrie aceasta imagine in detaliu. Raspunde doar in limba romana." },
            el: { title: "AI Περιγραφέας Εικόνων", subtitle: "Ανεβάστε μια εικόνα και αφήστε το Gemma 4 να την περιγράψει", langLabel: "Γλώσσα:", upload: "Σύρετε μια εικόνα εδώ ή κάντε κλικ για ανέβασμα", formats: "Υποστηρίζει JPG, PNG, GIF, WebP, BMP", placeholder: "Περιγράψτε αυτή την εικόνα λεπτομερώς (ή πληκτρολογήστε το δικό σας prompt)", btn: "Περιγραφή", loading: "Το Gemma 4 αναλύει την εικόνα...", result: "Περιγραφή", another: "Περιγράψτε άλλη εικόνα", promptPrefix: "Περιγράψτε αυτή την εικόνα λεπτομερώς. Απαντήστε μόνο στα ελληνικά." },
            hu: { title: "AI Kepeliro", subtitle: "Toltsön fel egy kepet es hagyja, hogy a Gemma 4 leirja", langLabel: "Nyelv:", upload: "Huzzon ide egy kepet vagy kattintson a feltolteshez", formats: "Tamogatja: JPG, PNG, GIF, WebP, BMP", placeholder: "Irja le ezt a kepet reszletesen (vagy irja be sajat kereset)", btn: "Leiras", loading: "A Gemma 4 elemzi a kepet...", result: "Leiras", another: "Masik kep leirasa", promptPrefix: "Ird le ezt a kepet reszletesen. Csak magyarul valaszolj." },
            cs: { title: "AI Popis Obrazku", subtitle: "Nahrajte obrazek a nechte Gemma 4 ho popsat", langLabel: "Jazyk:", upload: "Pretahnete obrazek sem nebo kliknete pro nahrani", formats: "Podporuje JPG, PNG, GIF, WebP, BMP", placeholder: "Popiste tento obrazek podrobne (nebo zadejte vlastni prompt)", btn: "Popsat", loading: "Gemma 4 analyzuje obrazek...", result: "Popis", another: "Popsat dalsi obrazek", promptPrefix: "Popis tento obrazek podrobne. Odpovez pouze v cestine." },
            da: { title: "AI Billedbeskriver", subtitle: "Upload et billede og lad Gemma 4 beskrive det", langLabel: "Sprog:", upload: "Traek et billede hertil eller klik for at uploade", formats: "Understotter JPG, PNG, GIF, WebP, BMP", placeholder: "Beskriv dette billede detaljeret (eller skriv din egen prompt)", btn: "Beskriv", loading: "Gemma 4 analyserer billedet...", result: "Beskrivelse", another: "Beskriv et andet billede", promptPrefix: "Beskriv dette billede detaljeret. Svar kun pa dansk." },
            fi: { title: "AI Kuvanselittaja", subtitle: "Lataa kuva ja anna Gemma 4:n kuvailla se", langLabel: "Kieli:", upload: "Vedä kuva tähän tai napsauta ladataksesi", formats: "Tukee JPG, PNG, GIF, WebP, BMP", placeholder: "Kuvaile tämä kuva yksityiskohtaisesti (tai kirjoita oma kehotteesi)", btn: "Kuvaile", loading: "Gemma 4 analysoi kuvaa...", result: "Kuvaus", another: "Kuvaile toinen kuva", promptPrefix: "Kuvaile tämä kuva yksityiskohtaisesti. Vastaa vain suomeksi." },
            no: { title: "AI Bildebeskriver", subtitle: "Last opp et bilde og la Gemma 4 beskrive det", langLabel: "Sprak:", upload: "Slipp et bilde her eller klikk for a laste opp", formats: "Stotter JPG, PNG, GIF, WebP, BMP", placeholder: "Beskriv dette bildet i detalj (eller skriv din egen prompt)", btn: "Beskriv", loading: "Gemma 4 analyserer bildet...", result: "Beskrivelse", another: "Beskriv et annet bilde", promptPrefix: "Beskriv dette bildet i detalj. Svar kun pa norsk." },
        };

        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const previewSection = document.getElementById('previewSection');
        const previewImg = document.getElementById('previewImg');
        const promptRow = document.getElementById('promptRow');
        const promptInput = document.getElementById('promptInput');
        const loading = document.getElementById('loading');
        const resultSection = document.getElementById('resultSection');
        const resultText = document.getElementById('resultText');
        const describeBtn = document.getElementById('describeBtn');
        const newBtn = document.getElementById('newBtn');
        const langSelect = document.getElementById('langSelect');

        let currentFile = null;
        let currentLang = 'en';

        function switchLang() {
            currentLang = langSelect.value;
            const t = TRANSLATIONS[currentLang] || TRANSLATIONS['en'];
            const isRtl = RTL_LANGS.has(currentLang);

            document.documentElement.lang = currentLang;
            document.body.dir = isRtl ? 'rtl' : 'ltr';
            document.getElementById('title').textContent = t.title;
            document.getElementById('subtitle').textContent = t.subtitle;
            document.getElementById('langLabel').textContent = t.langLabel;
            document.getElementById('uploadText').textContent = t.upload;
            document.getElementById('formatsText').textContent = t.formats;
            promptInput.placeholder = t.placeholder;
            describeBtn.textContent = t.btn;
            document.getElementById('loadingText').textContent = t.loading;
            document.getElementById('resultTitle').textContent = t.result;
            document.getElementById('newBtnText').textContent = t.another;
        }

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', e => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });
        promptInput.addEventListener('keydown', e => { if (e.key === 'Enter') describeImage(); });

        function handleFile(file) {
            if (!file.type.startsWith('image/')) { alert('Please upload an image file.'); return; }
            currentFile = file;
            const reader = new FileReader();
            reader.onload = e => {
                previewImg.src = e.target.result;
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('fileSize').textContent = formatSize(file.size);
                uploadArea.style.display = 'none';
                previewSection.classList.add('active');
                promptRow.classList.add('active');
                resultSection.classList.remove('active');
                newBtn.classList.remove('active');
                promptInput.focus();
            };
            reader.readAsDataURL(file);
        }

        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1048576).toFixed(1) + ' MB';
        }

        async function describeImage() {
            if (!currentFile) return;
            const t = TRANSLATIONS[currentLang] || TRANSLATIONS['en'];
            const userPrompt = promptInput.value.trim();
            const prompt = userPrompt ? userPrompt + ' ' + t.promptPrefix : t.promptPrefix;

            describeBtn.disabled = true;
            loading.classList.add('active');
            resultSection.classList.remove('active');

            const formData = new FormData();
            formData.append('image', currentFile);
            formData.append('prompt', prompt);

            try {
                const resp = await fetch('/describe', { method: 'POST', body: formData });
                const data = await resp.json();
                if (data.error) {
                    resultText.textContent = 'Error: ' + data.error;
                } else {
                    resultText.textContent = data.description;
                }
            } catch (err) {
                resultText.textContent = 'Error: Could not connect to server.';
            }
            loading.classList.remove('active');
            resultSection.classList.add('active');
            newBtn.classList.add('active');
            describeBtn.disabled = false;
        }

        function resetAll() {
            currentFile = null;
            fileInput.value = '';
            uploadArea.style.display = '';
            previewSection.classList.remove('active');
            promptRow.classList.remove('active');
            resultSection.classList.remove('active');
            newBtn.classList.remove('active');
            promptInput.value = '';
            resultText.textContent = '';
        }
    </script>
</body>
</html>"""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path != "/describe":
            self.send_error(404)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json_response({"error": "Invalid request"})
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
        )

        image_field = form["image"]
        prompt = form.getvalue("prompt", "Describe this image in detail.")
        image_data = image_field.file.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._json_response({"description": result["response"]})
        except Exception as e:
            self._json_response({"error": str(e)})

    def _json_response(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"AI Image Describer running at http://localhost:{PORT}")
    print(f"Model: {MODEL}")
    print("Press Ctrl+C to stop\n")
    server.serve_forever()
