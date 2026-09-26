/**
 * SmartFarm AI — Client-side i18n
 * Centralized translations loaded from translations/ directory.
 * Language is persisted to localStorage under 'smartfarm.language'.
 */
(function (window) {
  'use strict';

  const STORAGE_KEY = 'smartfarm.language';
  const DEFAULT_LANG = 'en';

  const LANGUAGES = [
    { code: 'en', label: 'English',  native: 'English',   bcp47: 'en-US' },
    { code: 'hi', label: 'Hindi',    native: 'हिन्दी',     bcp47: 'hi-IN' },
    { code: 'te', label: 'Telugu',   native: 'తెలుగు',     bcp47: 'te-IN' },
    { code: 'ta', label: 'Tamil',    native: 'தமிழ்',      bcp47: 'ta-IN' },
    { code: 'bn', label: 'Bengali',  native: 'বাংলা',      bcp47: 'bn-IN' },
    { code: 'mr', label: 'Marathi',  native: 'मराठी',      bcp47: 'mr-IN' },
    { code: 'kn', label: 'Kannada',  native: 'ಕನ್ನಡ',      bcp47: 'kn-IN' },
    { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી',    bcp47: 'gu-IN' },
  ];

  const _en = {
  "nav.analyze": "Analyze",
  "nav.history": "History",
  "nav.language": "Language",
  "nav.selectLanguage": "Select language",
  "page.title.home": "SmartFarm AI — Plant Disease Detection",
  "page.title.history": "Scan History — SmartFarm AI",
  "page.title.detail": "Scan Report — SmartFarm AI",
  "hero.tag": "SmartFarm AI · Plant Pathology, Pocket-Sized",
  "hero.title1": "Diagnose plant disease",
  "hero.title2": "from a single leaf.",
  "hero.subtitle": "Upload a photo of a leaf and get an agronomist-style report — predicted disease, confidence, water stress, and step-by-step recommendations. No sensors, no jargon.",
  "hero.cta": "Analyze a leaf",
  "hero.howCta": "How it works",
  "hero.stat1": "disease classes",
  "hero.stat2": "avg analysis",
  "hero.stat3": "exportable",
  "how.step1.overline": "Step 01",
  "how.step1.title": "Snap",
  "how.step1.text": "Upload a clear close-up of a single leaf — JPEG, PNG or WEBP.",
  "how.step2.overline": "Step 02",
  "how.step2.title": "Scan",
  "how.step2.text": "Our vision model inspects color, texture and shape for disease signatures.",
  "how.step3.overline": "Step 03",
  "how.step3.title": "Solve",
  "how.step3.text": "Get an agronomist-style report with actions you can take today.",
  "analyzer.overline": "Analyzer",
  "analyzer.title": "Upload a leaf. Get a report.",
  "analyzer.subtitle": "Best with a close, well-lit shot of a single leaf. Add the crop name if you know it — we'll factor it in.",
  "uploader.dropTitle": "Drop a leaf photo here",
  "uploader.dropSubtitle": "JPEG, PNG or WEBP up to 8MB. Close-up shots of a single leaf give the best results.",
  "uploader.orBrowse": "or click to browse",
  "uploader.dropAria": "Click or drag and drop to upload leaf image",
  "uploader.previewAlt": "Leaf preview",
  "uploader.clearAria": "Remove image",
  "uploader.step1": "Step 1",
  "uploader.tellUs": "Tell us about your plant",
  "uploader.cropLabel": "Crop name (optional)",
  "uploader.cropPlaceholder": "e.g. Tomato, Basil, Pepper",
  "uploader.cropHint": "Helps the model contextualize symptoms — leave blank if unsure.",
  "uploader.tip1": "Take photo in daylight, flat against the leaf.",
  "uploader.tip2": "Frame a single leaf, fill most of the frame.",
  "uploader.tip3": "Avoid blur, glare, and heavy filters.",
  "uploader.analyzeBtn": "Analyze Leaf",
  "uploader.analyzing": "Analyzing…",
  "uploader.analyzingLeaf": "Analyzing leaf…",
  "uploader.poweredBy": "Powered by Gemini Flash vision · ~10–25s per analysis",
  "uploader.err.formats": "Only JPEG, PNG, or WEBP images are supported.",
  "uploader.err.tooLarge": "Image must be 8MB or smaller.",
  "uploader.err.noFile": "Please choose a leaf image first.",
  "uploader.err.generic": "Could not analyze image",
  "uploader.toast.done": "Analysis complete",
  "gallery.overline": "Common Issues",
  "gallery.title": "Know the signs",
  "gallery.subtitle": "A quick visual primer of frequent plant ailments urban farmers encounter.",
  "gallery.c1.crop": "Tomato",
  "gallery.c1.disease": "Early Blight",
  "gallery.c1.desc": "Dark concentric rings on lower leaves",
  "gallery.c2.crop": "Cucurbits",
  "gallery.c2.disease": "Powdery Mildew",
  "gallery.c2.desc": "White powdery patches on leaf surface",
  "gallery.c3.crop": "Pepper / Chili",
  "gallery.c3.disease": "Leaf Curl",
  "gallery.c3.desc": "Upward curling and yellowing margins",
  "gallery.c4.crop": "Any",
  "gallery.c4.disease": "Water Stress",
  "gallery.c4.desc": "Wilting, dull color, dry leaf tips",
  "report.overline": "Plant Health Report",
  "report.health": "Health Status",
  "report.disease": "Predicted Disease",
  "report.confidence": "Confidence",
  "report.water": "Water Stress",
  "report.severity": "Severity Assessment",
  "report.symptoms": "Detected Symptoms",
  "report.actions": "Recommended Actions",
  "report.preventive": "Preventive Measures",
  "report.notes": "Notes",
  "report.download": "Download PDF",
  "report.newScan": "New scan",
  "report.speak": "Listen",
  "report.stop": "Stop",
  "report.noSymptoms": "No specific symptoms detected.",
  "report.noActions": "No actions required at this time.",
  "report.dash": "—",
  "report.notPlant": "This image does not appear to be a plant leaf. Results may not be meaningful — try uploading a close-up of a single leaf.",
  "report.cropHint": "Crop hint",
  "report.leafImgAlt": "Analyzed leaf",
  "status.Healthy": "Healthy",
  "status.Unhealthy": "Unhealthy",
  "status.Uncertain": "Uncertain",
  "stress.Low": "Low",
  "stress.Moderate": "Moderate",
  "stress.High": "High",
  "stress.Critical": "Critical",
  "history.overline": "Archive",
  "history.title": "Scan History",
  "history.subtitle": "A chronological record of every leaf you've analyzed. Tap a card to revisit the full report.",
  "history.newScan": "New scan",
  "history.empty.title": "No scans yet",
  "history.empty.text": "Run your first leaf analysis to start your archive.",
  "history.empty.cta": "Analyze a leaf",
  "history.confirmDelete": "Delete this scan?",
  "history.crop": "Crop",
  "history.pdfBtn": "PDF",
  "history.deleteAria": "Delete scan",
  "history.toast.loadFail": "Could not load history",
  "history.toast.deleted": "Scan deleted",
  "history.toast.deleteFail": "Delete failed",
  "history.toast.pdfFail": "Could not download report",
  "detail.back": "Back to history",
  "detail.loading": "Loading report…",
  "detail.notFound": "Scan not found",
  "footer.tag": "Diagnose plant disease and water stress from a single leaf photo — no sensors, no spreadsheets.",
  "footer.builtFor": "Built for",
  "footer.role1": "Urban gardeners",
  "footer.role2": "Hobby farmers",
  "footer.role3": "Community plots",
  "footer.disclaimer": "Disclaimer",
  "footer.disclaimerText": "Reports are informational and based on visible symptoms. They do not replace lab diagnosis or professional agronomy advice.",
  "pdf.title": "SmartFarm AI — Plant Health Report",
  "pdf.generated": "Generated:",
  "pdf.crop": "Crop:",
  "pdf.status": "Status",
  "pdf.disease": "Disease",
  "pdf.confidence": "Confidence",
  "pdf.water": "Water Stress",
  "pdf.severity": "Severity Assessment",
  "pdf.symptoms": "Detected Symptoms",
  "pdf.actions": "Recommended Actions",
  "pdf.preventive": "Preventive Measures",
  "pdf.notes": "Notes",
  "pdf.footer": "SmartFarm AI — Plant health analysis is informational and does not replace professional agronomy advice.",
  "ml.disease.Healthy": "Healthy",
  "ml.disease.Late Blight": "Late Blight",
  "ml.disease.Early Blight": "Early Blight",
  "ml.disease.Leaf Mold": "Leaf Mold",
  "ml.disease.Septoria Leaf Spot": "Septoria Leaf Spot",
  "ml.disease.Bacterial Spot": "Bacterial Spot",
  "ml.disease.Unhealthy (Unknown Type)": "Unhealthy (Unknown Type)",
  "ml.disease.Uncertain": "Uncertain",
  "ml.disease.Uncertain Result - Manual Verification Recommended": "Uncertain Result - Manual Verification Recommended",
  "ml.disease.Analysis unavailable": "Analysis unavailable",
  "ml.symptom.Brown spots": "Brown spots",
  "ml.symptom.Yellow patches": "Yellow patches",
  "ml.symptom.Lesions": "Lesions",
  "ml.symptom.Mold": "Mold",
  "ml.symptom.Wilting": "Wilting",
  "ml.symptom.Curling": "Curling",
  "ml.symptom.Discoloration": "Discoloration",
  "ml.symptom.No visible disease symptoms": "No visible disease symptoms",
  "ml.symptom.Uniform green color": "Uniform green color",
  "ml.symptom.No lesions or spots": "No lesions or spots",
  "ml.symptom.Water-soaked lesions": "Water-soaked lesions",
  "ml.symptom.Circular lesions": "Circular lesions",
  "ml.symptom.Powdery coating": "Powdery coating",
  "ml.symptom.Small brown spots": "Small brown spots",
  "ml.symptom.Water-soaked spots": "Water-soaked spots",
  "ml.symptom.Insufficient evidence for classification": "Insufficient evidence for classification",
  "ml.symptom.Analysis error": "Analysis error",
  "ml.symptom.Manual verification required": "Manual verification required",
  "ml.symptom.Image analysis error occurred": "Image analysis error occurred",
  "ml.symptom.AI vision service temporarily unavailable": "AI vision service temporarily unavailable",
  "ml.symptom.Please try again later": "Please try again later",
  "ml.action.Maintain current watering schedule": "Maintain current watering schedule",
  "ml.action.Monitor for any changes in leaf appearance": "Monitor for any changes in leaf appearance",
  "ml.action.Maintain proper plant nutrition": "Maintain proper plant nutrition",
  "ml.action.Remove and destroy affected plants immediately": "Remove and destroy affected plants immediately",
  "ml.action.Apply fungicide containing chlorothalonil": "Apply fungicide containing chlorothalonil",
  "ml.action.Avoid working with plants when wet": "Avoid working with plants when wet",
  "ml.action.Rotate crops to prevent recurrence": "Rotate crops to prevent recurrence",
  "ml.action.Remove affected leaves to prevent spread": "Remove affected leaves to prevent spread",
  "ml.action.Apply copper-based fungicide": "Apply copper-based fungicide",
  "ml.action.Improve air circulation around plants": "Improve air circulation around plants",
  "ml.action.Avoid overhead watering": "Avoid overhead watering",
  "ml.action.Improve air circulation significantly": "Improve air circulation significantly",
  "ml.action.Reduce humidity around plants": "Reduce humidity around plants",
  "ml.action.Remove affected lower leaves": "Remove affected lower leaves",
  "ml.action.Apply fungicide if severe": "Apply fungicide if severe",
  "ml.action.Remove infected leaves immediately": "Remove infected leaves immediately",
  "ml.action.Mulch to prevent splash dispersal": "Mulch to prevent splash dispersal",
  "ml.action.Remove infected plant material": "Remove infected plant material",
  "ml.action.Apply copper-based bactericide": "Apply copper-based bactericide",
  "ml.action.Disinfect tools between uses": "Disinfect tools between uses",
  "ml.action.Inspect plant closely for additional symptoms": "Inspect plant closely for additional symptoms",
  "ml.action.Consult agricultural extension service": "Consult agricultural extension service",
  "ml.action.Isolate affected plant if possible": "Isolate affected plant if possible",
  "ml.action.Monitor for spread to other plants": "Monitor for spread to other plants",
  "ml.action.Inspect plant closely for symptoms": "Inspect plant closely for symptoms",
  "ml.action.Consult agricultural extension": "Consult agricultural extension",
  "ml.action.Monitor for changes in plant condition": "Monitor for changes in plant condition",
  "ml.action.Check leaf for visible spots or discoloration": "Check leaf for visible spots or discoloration",
  "ml.action.Ensure proper watering and sunlight": "Ensure proper watering and sunlight",
  "ml.action.Consult local agricultural extension if symptoms persist": "Consult local agricultural extension if symptoms persist",
  "ml.action.Try uploading the image again": "Try uploading the image again",
  "ml.action.Increase watering frequency slightly": "Increase watering frequency slightly",
  "ml.action.Check soil moisture regularly": "Check soil moisture regularly",
  "ml.action.Increase watering significantly": "Increase watering significantly",
  "ml.action.Add mulch to retain moisture": "Add mulch to retain moisture",
  "ml.action.Provide shade during peak heat": "Provide shade during peak heat",
  "ml.action.Immediate deep watering required": "Immediate deep watering required",
  "ml.action.Consider plant recovery measures": "Consider plant recovery measures",
  "ml.action.Protect from direct sunlight": "Protect from direct sunlight",
  "ml.preventive.Regularly inspect plants for early signs of disease": "Regularly inspect plants for early signs of disease",
  "ml.preventive.Maintain proper spacing between plants": "Maintain proper spacing between plants",
  "ml.preventive.Ensure good air circulation": "Ensure good air circulation",
  "ml.preventive.Use certified disease-free seeds": "Use certified disease-free seeds",
  "ml.preventive.Plant resistant varieties": "Plant resistant varieties",
  "ml.preventive.Ensure good drainage": "Ensure good drainage",
  "ml.preventive.Avoid overhead irrigation": "Avoid overhead irrigation",
  "ml.preventive.Space plants properly for airflow": "Space plants properly for airflow",
  "ml.preventive.Water at base of plants, not leaves": "Water at base of plants, not leaves",
  "ml.preventive.Remove plant debris regularly": "Remove plant debris regularly",
  "ml.preventive.Use disease-resistant varieties": "Use disease-resistant varieties",
  "ml.preventive.Avoid overcrowding": "Avoid overcrowding",
  "ml.preventive.Ensure good ventilation": "Ensure good ventilation",
  "ml.preventive.Water at soil level only": "Water at soil level only",
  "ml.preventive.Rotate crops annually": "Rotate crops annually",
  "ml.preventive.Space plants properly": "Space plants properly",
  "ml.preventive.Remove plant debris in fall": "Remove plant debris in fall",
  "ml.preventive.Use disease-free seeds and transplants": "Use disease-free seeds and transplants",
  "ml.preventive.Control insect vectors": "Control insect vectors",
  "ml.preventive.Regular plant inspections": "Regular plant inspections",
  "ml.preventive.Maintain proper sanitation": "Maintain proper sanitation",
  "ml.preventive.Quarantine new plants": "Quarantine new plants",
  "ml.preventive.Keep garden area clean": "Keep garden area clean",
  "ml.preventive.Maintain proper plant care practices": "Maintain proper plant care practices",
  "ml.preventive.Avoid overhead watering to reduce fungal risk": "Avoid overhead watering to reduce fungal risk"
};

  const _hi = {
  "nav.analyze": "विश्लेषण",
  "nav.history": "इतिहास",
  "nav.language": "भाषा",
  "nav.selectLanguage": "भाषा चुनें",
  "page.title.home": "स्मार्टफार्म एआई — पौधा रोग पहचान",
  "page.title.history": "स्कैन इतिहास — स्मार्टफार्म एआई",
  "page.title.detail": "स्कैन रिपोर्ट — स्मार्टफार्म एआई",
  "hero.tag": "स्मार्टफार्म एआई · जेब में पौधा विज्ञान",
  "hero.title1": "पौधे की बीमारी पहचानें",
  "hero.title2": "एक पत्ती की तस्वीर से।",
  "hero.subtitle": "पत्ती की एक तस्वीर अपलोड करें और कृषि विशेषज्ञ जैसी रिपोर्ट पाएं — संभावित बीमारी, विश्वास स्तर, जल तनाव और चरण-दर-चरण सुझाव। बिना सेंसर, बिना जटिलता।",
  "hero.cta": "पत्ती का विश्लेषण करें",
  "hero.howCta": "यह कैसे काम करता है",
  "hero.stat1": "बीमारी वर्ग",
  "hero.stat2": "औसत विश्लेषण समय",
  "hero.stat3": "एक्सपोर्ट करने योग्य",
  "how.step1.overline": "चरण 01",
  "how.step1.title": "तस्वीर लें",
  "how.step1.text": "एक पत्ती की स्पष्ट और नज़दीकी तस्वीर अपलोड करें — JPEG, PNG या WEBP।",
  "how.step2.overline": "चरण 02",
  "how.step2.title": "स्कैन करें",
  "how.step2.text": "हमारा विजन मॉडल बीमारी के लक्षणों के लिए रंग, बनावट और आकार की जांच करता है।",
  "how.step3.overline": "चरण 03",
  "how.step3.title": "समाधान पाएं",
  "how.step3.text": "व्यावहारिक सुझावों और कदमों के साथ कृषि विशेषज्ञ जैसी रिपोर्ट प्राप्त करें।",
  "analyzer.overline": "विश्लेषक",
  "analyzer.title": "पत्ती अपलोड करें। रिपोर्ट पाएं।",
  "analyzer.subtitle": "एक पत्ती की नज़दीकी और अच्छी रोशनी वाली तस्वीर सबसे बेहतर है। यदि आपको फसल का नाम पता है तो दर्ज करें।",
  "uploader.dropTitle": "यहाँ पत्ती की तस्वीर डालें",
  "uploader.dropSubtitle": "JPEG, PNG या WEBP 8MB तक। एक पत्ती की नज़दीकी तस्वीर सबसे अच्छे परिणाम देती है।",
  "uploader.orBrowse": "या चुनने के लिए क्लिक करें",
  "uploader.dropAria": "पत्ती की छवि अपलोड करने के लिए क्लिक करें या खींचकर छोड़ें",
  "uploader.previewAlt": "पत्ती का पूर्वावलोकन",
  "uploader.clearAria": "तस्वीर हटाएं",
  "uploader.step1": "चरण 1",
  "uploader.tellUs": "अपने पौधे के बारे में बताएं",
  "uploader.cropLabel": "फसल का नाम (वैकल्पिक)",
  "uploader.cropPlaceholder": "जैसे टमाटर, तुलसी, मिर्च",
  "uploader.cropHint": "लक्षणों को सटीक समझने में मदद करता है — सुनिश्चित न होने पर खाली छोड़ दें।",
  "uploader.tip1": "दिन के उजाले में पत्ती की सीधी तस्वीर लें।",
  "uploader.tip2": "एक ही पत्ती को फ्रेम में रखें और अधिकांश हिस्सा कवर करें।",
  "uploader.tip3": "धुंधलापन, चमक और भारी फिल्टर से बचें।",
  "uploader.analyzeBtn": "पत्ती का विश्लेषण करें",
  "uploader.analyzing": "विश्लेषण हो रहा है…",
  "uploader.analyzingLeaf": "पत्ती का विश्लेषण हो रहा है…",
  "uploader.poweredBy": "जेमिनी फ्लैश विजन द्वारा संचालित · लगभग 10-25 सेकंड प्रति विश्लेषण",
  "uploader.err.formats": "केवल JPEG, PNG या WEBP छवियां समर्थित हैं।",
  "uploader.err.tooLarge": "छवि 8MB या उससे छोटी होनी चाहिए।",
  "uploader.err.noFile": "कृपया पहले एक पत्ती की छवि चुनें।",
  "uploader.err.generic": "छवि का विश्लेषण नहीं किया जा सका",
  "uploader.toast.done": "विश्लेषण पूर्ण हुआ",
  "gallery.overline": "सामान्य समस्याएं",
  "gallery.title": "लक्षणों को पहचानें",
  "gallery.subtitle": "शहरी किसानों द्वारा सामना की जाने वाली सामान्य पौध बीमारियों की एक संक्षिप्त झलक।",
  "gallery.c1.crop": "टमाटर",
  "gallery.c1.disease": "अगेती झुलसा",
  "gallery.c1.desc": "निचली पत्तियों पर काले छल्लेदार घेरे",
  "gallery.c2.crop": "ककड़ी/कद्दू वर्ग",
  "gallery.c2.disease": "पाउडरी मिल्ड्यू (चूर्णिल आसिता)",
  "gallery.c2.desc": "पत्ती की सतह पर सफेद पाउडर जैसे धब्बे",
  "gallery.c3.crop": "शिमला मिर्च / मिर्च",
  "gallery.c3.disease": "पत्ती मरोड़ रोग (लीफ कर्ल)",
  "gallery.c3.desc": "किनारों का ऊपर की ओर मुड़ना और पीला पड़ना",
  "gallery.c4.crop": "कोई भी पौधा",
  "gallery.c4.disease": "जल तनाव",
  "gallery.c4.desc": "मुरझाना, फीका रंग और पत्ती के सूखे सिरे",
  "report.overline": "पौधा स्वास्थ्य रिपोर्ट",
  "report.health": "स्वास्थ्य स्थिति",
  "report.disease": "संभावित बीमारी",
  "report.confidence": "विश्वास",
  "report.water": "जल तनाव",
  "report.severity": "गंभीरता आकलन",
  "report.symptoms": "पहचाने गए लक्षण",
  "report.actions": "अनुशंसित कार्रवाई",
  "report.preventive": "रोकथाम के उपाय",
  "report.notes": "टिप्पणी",
  "report.download": "PDF डाउनलोड",
  "report.newScan": "नया स्कैन",
  "report.speak": "सुनें",
  "report.stop": "रोकें",
  "report.noSymptoms": "कोई विशिष्ट लक्षण नहीं मिले।",
  "report.noActions": "इस समय किसी कार्रवाई की आवश्यकता नहीं है।",
  "report.dash": "—",
  "report.notPlant": "यह तस्वीर पौधे की पत्ती जैसी नहीं लगती। परिणाम सटीक नहीं हो सकते — कृपया एक पत्ती की नज़दीकी तस्वीर अपलोड करें।",
  "report.cropHint": "फसल का संकेत",
  "report.leafImgAlt": "विश्लेषित पत्ती",
  "status.Healthy": "स्वस्थ",
  "status.Unhealthy": "अस्वस्थ",
  "status.Uncertain": "अनिश्चित",
  "stress.Low": "कम",
  "stress.Moderate": "मध्यम",
  "stress.High": "अधिक",
  "stress.Critical": "गंभीर",
  "history.overline": "संग्रह",
  "history.title": "स्कैन इतिहास",
  "history.subtitle": "आपके द्वारा विश्लेषित हर पत्ती का कालानुक्रमिक रिकॉर्ड। पूरी रिपोर्ट देखने के लिए कार्ड पर टैप करें।",
  "history.newScan": "नया स्कैन",
  "history.empty.title": "अभी कोई स्कैन नहीं है",
  "history.empty.text": "अपना संग्रह शुरू करने के लिए पहली पत्ती का विश्लेषण करें।",
  "history.empty.cta": "पत्ती का विश्लेषण करें",
  "history.confirmDelete": "क्या इस स्कैन को हटाना चाहते हैं?",
  "history.crop": "फसल",
  "history.pdfBtn": "PDF",
  "history.deleteAria": "स्कैन हटाएं",
  "history.toast.loadFail": "इतिहास लोड नहीं किया जा सका",
  "history.toast.deleted": "स्कैन हटा दिया गया",
  "history.toast.deleteFail": "हटाना विफल रहा",
  "history.toast.pdfFail": "रिपोर्ट डाउनलोड नहीं की जा सकी",
  "detail.back": "इतिहास पर वापस",
  "detail.loading": "रिपोर्ट लोड हो रही है…",
  "detail.notFound": "स्कैन नहीं मिला",
  "footer.tag": "एक पत्ती की तस्वीर से पौधे की बीमारी और जल तनाव पहचानें — बिना सेंसर, बिना जटिलता।",
  "footer.builtFor": "इनके लिए निर्मित",
  "footer.role1": "शहरी माली",
  "footer.role2": "शौकिया किसान",
  "footer.role3": "सामुदायिक खेत",
  "footer.disclaimer": "अस्वीकरण",
  "footer.disclaimerText": "रिपोर्ट केवल जानकारी के लिए हैं और दिखने वाले लक्षणों पर आधारित हैं। वे प्रयोगशाला निदान या पेशेवर कृषि सलाह का विकल्प नहीं हैं।",
  "pdf.title": "स्मार्टफार्म एआई — पौधा स्वास्थ्य रिपोर्ट",
  "pdf.generated": "उत्पन्न:",
  "pdf.crop": "फसल:",
  "pdf.status": "स्थिति",
  "pdf.disease": "बीमारी",
  "pdf.confidence": "विश्वास",
  "pdf.water": "जल तनाव",
  "pdf.severity": "गंभीरता आकलन",
  "pdf.symptoms": "पहचाने गए लक्षण",
  "pdf.actions": "अनुशंसित कार्रवाई",
  "pdf.preventive": "रोकथाम के उपाय",
  "pdf.notes": "टिप्पणी",
  "pdf.footer": "स्मार्टफार्म एआई — पौधा स्वास्थ्य विश्लेषण केवल जानकारी के लिए है और पेशेवर कृषि सलाह का विकल्प नहीं है।",
  "ml.disease.Healthy": "स्वस्थ",
  "ml.disease.Late Blight": "पछेती झुलसा (लेट ब्लाइट)",
  "ml.disease.Early Blight": "अगेती झुलसा (अर्ली ब्लाइट)",
  "ml.disease.Leaf Mold": "पत्ती की फफूंद (लीफ मोल्ड)",
  "ml.disease.Septoria Leaf Spot": "सेप्टोरिया पत्ती धब्बा",
  "ml.disease.Bacterial Spot": "जीवाणु धब्बा (बैक्टीरियल स्पॉट)",
  "ml.disease.Unhealthy (Unknown Type)": "अस्वस्थ (अज्ञात प्रकार)",
  "ml.disease.Uncertain": "अनिश्चित",
  "ml.disease.Uncertain Result - Manual Verification Recommended": "अनिश्चित परिणाम - मैन्युअल सत्यापन अनुशंसित",
  "ml.disease.Analysis unavailable": "विश्लेषण अनुपलब्ध",
  "ml.symptom.Brown spots": "भूरे धब्बे",
  "ml.symptom.Yellow patches": "पीले धब्बे",
  "ml.symptom.Lesions": "घाव/क्षति",
  "ml.symptom.Mold": "फफूंद",
  "ml.symptom.Wilting": "मुरझाना",
  "ml.symptom.Curling": "पत्तियों का मुड़ना",
  "ml.symptom.Discoloration": "रंग उड़ना / विवर्णता",
  "ml.symptom.No visible disease symptoms": "बीमारी के कोई प्रत्यक्ष लक्षण नहीं",
  "ml.symptom.Uniform green color": "एकसमान हरा रंग",
  "ml.symptom.No lesions or spots": "कोई घाव या धब्बे नहीं",
  "ml.symptom.Water-soaked lesions": "पानी से भीगे हुए घाव",
  "ml.symptom.Circular lesions": "गोलाकार घाव",
  "ml.symptom.Powdery coating": "पाउडर जैसी परत",
  "ml.symptom.Small brown spots": "छोटे भूरे धब्बे",
  "ml.symptom.Water-soaked spots": "पानी से भीगे हुए धब्बे",
  "ml.symptom.Insufficient evidence for classification": "वर्गीकरण के लिए अपर्याप्त साक्ष्य",
  "ml.symptom.Analysis error": "विश्लेषण त्रुटि",
  "ml.symptom.Manual verification required": "मैन्युअल सत्यापन आवश्यक",
  "ml.symptom.Image analysis error occurred": "छवि विश्लेषण त्रुटि हुई",
  "ml.symptom.AI vision service temporarily unavailable": "एआई विजन सेवा अस्थायी रूप से अनुपलब्ध है",
  "ml.symptom.Please try again later": "कृपया बाद में पुन: प्रयास करें",
  "ml.action.Maintain current watering schedule": "वर्तमान पानी देने के समय को बनाए रखें",
  "ml.action.Monitor for any changes in leaf appearance": "पत्ती के स्वरूप में किसी भी बदलाव पर नज़र रखें",
  "ml.action.Maintain proper plant nutrition": "पौधों का उचित पोषण बनाए रखें",
  "ml.action.Remove and destroy affected plants immediately": "प्रभावित पौधों को तुरंत हटाकर नष्ट करें",
  "ml.action.Apply fungicide containing chlorothalonil": "क्लोरोथालोनिल युक्त कवकनाशी (फंगीसाइड) का प्रयोग करें",
  "ml.action.Avoid working with plants when wet": "पौधों के गीले होने पर उन पर काम करने से बचें",
  "ml.action.Rotate crops to prevent recurrence": "पुनरावृत्ति को रोकने के लिए फसल चक्र अपनाएं",
  "ml.action.Remove affected leaves to prevent spread": "फैलाव रोकने के लिए प्रभावित पत्तियों को हटा दें",
  "ml.action.Apply copper-based fungicide": "तांबा आधारित (कॉपर) कवकनाशी का प्रयोग करें",
  "ml.action.Improve air circulation around plants": "पौधों के आसपास वायु संचार में सुधार करें",
  "ml.action.Avoid overhead watering": "ऊपर से पानी देने से बचें (जड़ों में पानी दें)",
  "ml.action.Improve air circulation significantly": "वायु संचार में उल्लेखनीय सुधार करें",
  "ml.action.Reduce humidity around plants": "पौधों के आसपास की नमी कम करें",
  "ml.action.Remove affected lower leaves": "प्रभावित निचली पत्तियों को हटा दें",
  "ml.action.Apply fungicide if severe": "गंभीर होने पर कवकनाशी का प्रयोग करें",
  "ml.action.Remove infected leaves immediately": "संक्रमित पत्तियों को तुरंत हटा दें",
  "ml.action.Mulch to prevent splash dispersal": "मिट्टी के छींटों से फैलाव रोकने के लिए मल्चिंग करें",
  "ml.action.Remove infected plant material": "संक्रमित पौधे के हिस्सों को हटा दें",
  "ml.action.Apply copper-based bactericide": "तांबा आधारित जीवाणुनाशक (बैक्टीरीसाइड) का प्रयोग करें",
  "ml.action.Disinfect tools between uses": "उपयोग के बीच औजारों को कीटाणुरहित करें",
  "ml.action.Inspect plant closely for additional symptoms": "अतिरिक्त लक्षणों के लिए पौधे का बारीकी से निरीक्षण करें",
  "ml.action.Consult agricultural extension service": "कृषि विस्तार सेवा या कृषि विशेषज्ञ से परामर्श करें",
  "ml.action.Isolate affected plant if possible": "यदि संभव हो तो प्रभावित पौधे को अलग रखें",
  "ml.action.Monitor for spread to other plants": "अन्य पौधों में फैलाव पर नज़र रखें",
  "ml.action.Inspect plant closely for symptoms": "लक्षणों के लिए पौधे का बारीकी से निरीक्षण करें",
  "ml.action.Consult agricultural extension": "कृषि विस्तार सेवा से संपर्क करें",
  "ml.action.Monitor for changes in plant condition": "पौधे की स्थिति में बदलाव पर नज़र रखें",
  "ml.action.Check leaf for visible spots or discoloration": "दिखने वाले धब्बों या रंग उड़ने के लिए पत्ती की जांच करें",
  "ml.action.Ensure proper watering and sunlight": "उचित पानी और धूप सुनिश्चित करें",
  "ml.action.Consult local agricultural extension if symptoms persist": "यदि लक्षण बने रहते हैं तो स्थानीय कृषि विस्तार से परामर्श करें",
  "ml.action.Try uploading the image again": "छवि को पुनः अपलोड करने का प्रयास करें",
  "ml.action.Increase watering frequency slightly": "पानी देने की आवृत्ति थोड़ी बढ़ाएं",
  "ml.action.Check soil moisture regularly": "मिट्टी की नमी की नियमित जांच करें",
  "ml.action.Increase watering significantly": "पानी देने की मात्रा काफी बढ़ाएं",
  "ml.action.Add mulch to retain moisture": "नमी बनाए रखने के लिए मल्च जोड़ें",
  "ml.action.Provide shade during peak heat": "अत्यधिक गर्मी के समय छाया प्रदान करें",
  "ml.action.Immediate deep watering required": "तुरंत गहराई तक पानी देने की आवश्यकता है",
  "ml.action.Consider plant recovery measures": "पौधे को उबारने के उपायों पर विचार करें",
  "ml.action.Protect from direct sunlight": "सीधी तेज धूप से बचाएं",
  "ml.preventive.Regularly inspect plants for early signs of disease": "बीमारी के शुरुआती लक्षणों के लिए नियमित रूप से पौधों का निरीक्षण करें",
  "ml.preventive.Maintain proper spacing between plants": "पौधों के बीच उचित दूरी बनाए रखें",
  "ml.preventive.Ensure good air circulation": "अच्छा वायु संचार सुनिश्चित करें",
  "ml.preventive.Use certified disease-free seeds": "प्रमाणित रोगमुक्त बीजों का उपयोग करें",
  "ml.preventive.Plant resistant varieties": "रोग प्रतिरोधी किस्में लगाएं",
  "ml.preventive.Ensure good drainage": "जल निकासी की अच्छी व्यवस्था सुनिश्चित करें",
  "ml.preventive.Avoid overhead irrigation": "ऊपर से सिंचाई करने से बचें",
  "ml.preventive.Space plants properly for airflow": "वायु प्रवाह के लिए पौधों को उचित दूरी पर रखें",
  "ml.preventive.Water at base of plants, not leaves": "पत्तियों पर नहीं, पौधों की जड़ों में पानी दें",
  "ml.preventive.Remove plant debris regularly": "पौधों के सूखे अवशेष नियमित रूप से हटाएं",
  "ml.preventive.Use disease-resistant varieties": "रोग प्रतिरोधी किस्मों का प्रयोग करें",
  "ml.preventive.Avoid overcrowding": "पौधों की अत्यधिक भीड़भाड़ से बचें",
  "ml.preventive.Ensure good ventilation": "उचित वेंटिलेशन सुनिश्चित करें",
  "ml.preventive.Water at soil level only": "केवल मिट्टी के स्तर पर पानी दें",
  "ml.preventive.Rotate crops annually": "प्रतिवर्ष फसल चक्र अपनाएं",
  "ml.preventive.Space plants properly": "पौधों के बीच सही दूरी रखें",
  "ml.preventive.Remove plant debris in fall": "पतझड़ में पौधों के अवशेष हटा दें",
  "ml.preventive.Use disease-free seeds and transplants": "रोगमुक्त बीजों और पौधों का प्रयोग करें",
  "ml.preventive.Control insect vectors": "कीट वाहकों को नियंत्रित करें",
  "ml.preventive.Regular plant inspections": "नियमित पौधा निरीक्षण करें",
  "ml.preventive.Maintain proper sanitation": "उचित स्वच्छता बनाए रखें",
  "ml.preventive.Quarantine new plants": "नए पौधों को कुछ समय अलग (क्वारंटाइन) रखें",
  "ml.preventive.Keep garden area clean": "बगीचे के क्षेत्र को साफ रखें",
  "ml.preventive.Maintain proper plant care practices": "पौधों की उचित देखभाल की प्रथाएं बनाए रखें",
  "ml.preventive.Avoid overhead watering to reduce fungal risk": "फंगल जोखिम कम करने के लिए ऊपर से पानी देने से बचें"
};

  const _te = {
  "nav.analyze": "విశ్లేషణ",
  "nav.history": "చరిత్ర",
  "nav.language": "భాష",
  "nav.selectLanguage": "భాషను ఎంచుకోండి",
  "page.title.home": "స్మార్ట్‌ఫామ్ AI — మొక్కల వ్యాధి నిర్ధారణ",
  "page.title.history": "స్కాన్ చరిత్ర — స్మార్ట్‌ఫామ్ AI",
  "page.title.detail": "స్కాన్ నివేదిక — స్మార్ట్‌ఫామ్ AI",
  "hero.tag": "స్మార్ట్‌ఫామ్ AI · జేబు పరిమాణంలో మొక్కల రోగనిర్ధారణ",
  "hero.title1": "మొక్క వ్యాధిని గుర్తించండి",
  "hero.title2": "ఒకే ఒక్క ఆకు ద్వారా.",
  "hero.subtitle": "ఆకు ఫోటోను అప్‌లోడ్ చేసి, వ్యవసాయ నిపుణుల తరహా నివేదికను పొందండి — సంభావ్య వ్యాధి, ఖచ్చితత్వం, నీటి ఒత్తిడి మరియు దశలవారీ సిఫార్సులు. సెన్సార్లు లేకుండా, సాంకేతిక సంక్లిష్టత లేకుండా.",
  "hero.cta": "ఆకును విశ్లేషించండి",
  "hero.howCta": "ఇది ఎలా పనిచేస్తుంది",
  "hero.stat1": "వ్యాధి రకాలు",
  "hero.stat2": "సగటు విశ్లేషణ సమయం",
  "hero.stat3": "ఎగుమతి చేయదగినది",
  "how.step1.overline": "దశ 01",
  "how.step1.title": "ఫోటో తీయండి",
  "how.step1.text": "ఒకే ఆకు యొక్క స్పష్టమైన క్లోజప్ ఫోటోను అప్‌లోడ్ చేయండి — JPEG, PNG లేదా WEBP.",
  "how.step2.overline": "దశ 02",
  "how.step2.title": "స్కాన్ చేయండి",
  "how.step2.text": "మా విజన్ మోడల్ వ్యాధి లక్షణాల కోసం రంగు, ఆకృతి మరియు ఆకారాన్ని తనిఖీ చేస్తుంది.",
  "how.step3.overline": "దశ 03",
  "how.step3.title": "పరిష్కారం పొందండి",
  "how.step3.text": "ఈరోజే మీరు తీసుకోగల చర్యలతో కూడిన వ్యవసాయ నిపుణుల నివేదికను పొందండి.",
  "analyzer.overline": "విశ్లేషణ సాధనం",
  "analyzer.title": "ఆకును అప్‌లోడ్ చేయండి. నివేదిక పొందండి.",
  "analyzer.subtitle": "ఒకే ఆకు యొక్క స్పష్టమైన, మంచి వెలుతురు ఉన్న ఫోటో ఉత్తమం. పంట పేరు తెలిస్తే నమోదు చేయండి.",
  "uploader.dropTitle": "ఇక్కడ ఆకు ఫోటోను జారవేయండి",
  "uploader.dropSubtitle": "JPEG, PNG లేదా WEBP 8MB వరకు. ఒకే ఆకు క్లోజప్ షాట్లు ఉత్తమ ఫలితాలను ఇస్తాయి.",
  "uploader.orBrowse": "లేదా ఫైల్ ఎంచుకోవడానికి క్లిక్ చేయండి",
  "uploader.dropAria": "ఆకు చిత్రాన్ని అప్‌లోడ్ చేయడానికి క్లిక్ చేయండి లేదా డ్రాగ్ చేయండి",
  "uploader.previewAlt": "ఆకు ప్రివ్యూ",
  "uploader.clearAria": "చిత్రాన్ని తొలగించండి",
  "uploader.step1": "దశ 1",
  "uploader.tellUs": "మీ మొక్క గురించి చెప్పండి",
  "uploader.cropLabel": "పంట పేరు (ఐచ్ఛికం)",
  "uploader.cropPlaceholder": "ఉదా. టమాటా, తులసి, మిరప",
  "uploader.cropHint": "లక్షణాలను అర్థం చేసుకోవడానికి మోడల్‌కు సహాయపడుతుంది — ఖచ్చితంగా తెలియకపోతే ఖాళీగా ఉంచండి.",
  "uploader.tip1": "పగటి వెలుతురులో ఆకుకు సమాంతరంగా ఫోటో తీయండి.",
  "uploader.tip2": "ఒకే ఆకును ఫ్రేమ్‌లో ఉంచి, ఫోటోలో ఎక్కువ భాగం కనిపించేలా చూడండి.",
  "uploader.tip3": "మసకబారడం, మిరుమిట్లు మరియు ఫిల్టర్‌లను నివారించండి.",
  "uploader.analyzeBtn": "ఆకును విశ్లేషించండి",
  "uploader.analyzing": "విశ్లేషణ జరుగుతోంది…",
  "uploader.analyzingLeaf": "ఆకును విశ్లేషిస్తోంది…",
  "uploader.poweredBy": "జెమిని ఫ్లాష్ విజన్ ద్వారా ఆధారితం · విశ్లేషణకు ~10–25 సెకన్లు",
  "uploader.err.formats": "JPEG, PNG లేదా WEBP చిత్రాలు మాత్రమే మద్దతు ఇవ్వబడతాయి.",
  "uploader.err.tooLarge": "చిత్రం 8MB లేదా అంతకంటే తక్కువగా ఉండాలి.",
  "uploader.err.noFile": "దయచేసి ముందుగా ఆకు చిత్రాన్ని ఎంచుకోండి.",
  "uploader.err.generic": "చిత్రాన్ని విశ్లేషించలేకపోయాము",
  "uploader.toast.done": "విశ్లేషణ పూర్తయింది",
  "gallery.overline": "సాధారణ సమస్యలు",
  "gallery.title": "లక్షణాలను తెలుసుకోండి",
  "gallery.subtitle": "రైతులు తరచుగా ఎదుర్కొనే మొక్కల వ్యాధుల శీఘ్ర మార్గదర్శి.",
  "gallery.c1.crop": "టమాటా",
  "gallery.c1.disease": "ముందస్తు తెగులు (ఎర్లీ బ్లైట్)",
  "gallery.c1.desc": "దిగువ ఆకులపై ముదురు రంగు వలయాలు",
  "gallery.c2.crop": "దోస / గుమ్మడి రకాలు",
  "gallery.c2.disease": "బూడిద తెగులు (పౌడరీ మిల్డ్యూ)",
  "gallery.c2.desc": "ఆకు ఉపరితలంపై తెల్లటి పొడి మచ్చలు",
  "gallery.c3.crop": "మిరప",
  "gallery.c3.disease": "ఆకు ముడుత తెగులు (లీఫ్ కర్ల్)",
  "gallery.c3.desc": "ఆకులు పైకి ముడుచుకోవడం మరియు అంచులు పసుపు రంగులోకి మారడం",
  "gallery.c4.crop": "ఏదైనా మొక్క",
  "gallery.c4.disease": "నీటి ఒత్తిడి",
  "gallery.c4.desc": "వాడిపోవడం, రంగు తగ్గడం, ఆకుల కొనలు ఎండిపోవడం",
  "report.overline": "మొక్క ఆరోగ్య నివేదిక",
  "report.health": "ఆరోగ్య స్థితి",
  "report.disease": "సంభావ్య వ్యాధి",
  "report.confidence": "విశ్వాసం",
  "report.water": "నీటి ఒత్తిడి",
  "report.severity": "తీవ్రత అంచనా",
  "report.symptoms": "గుర్తించిన లక్షణాలు",
  "report.actions": "సిఫార్సు చేసిన చర్యలు",
  "report.preventive": "నివారణ చర్యలు",
  "report.notes": "వ్యాఖ్యలు",
  "report.download": "PDF డౌన్‌లోడ్",
  "report.newScan": "కొత్త స్కాన్",
  "report.speak": "వినండి",
  "report.stop": "ఆపండి",
  "report.noSymptoms": "ప్రత్యేక లక్షణాలు ఏవీ కనుగొనబడలేదు.",
  "report.noActions": "ప్రస్తుతం ఎటువంటి చర్యలు అవసరం లేదు.",
  "report.dash": "—",
  "report.notPlant": "ఈ చిత్రం మొక్క ఆకులా కనిపించడం లేదు. ఫలితాలు ఖచ్చితంగా ఉండకపోవచ్చు — దయచేసి ఒకే ఆకు యొక్క క్లోజప్ ఫోటోను అప్‌లోడ్ చేయండి.",
  "report.cropHint": "పంట సూచన",
  "report.leafImgAlt": "విశ్లేషించిన ఆకు",
  "status.Healthy": "ఆరోగ్యకరం",
  "status.Unhealthy": "అనారోగ్యకరం",
  "status.Uncertain": "అనిశ్చితం",
  "stress.Low": "తక్కువ",
  "stress.Moderate": "మధ్యస్థం",
  "stress.High": "అధికం",
  "stress.Critical": "తీవ్రం",
  "history.overline": "సంగ్రహం",
  "history.title": "స్కాన్ చరిత్ర",
  "history.subtitle": "మీరు విశ్లేషించిన ప్రతి ఆకు యొక్క చారిత్రక రికార్డు. పూర్తి నివేదికను చూడటానికి కార్డుపై నొక్కండి.",
  "history.newScan": "కొత్త స్కాన్",
  "history.empty.title": "ఇంకా స్కాన్‌లు లేవు",
  "history.empty.text": "మీ రికార్డును ప్రారంభించడానికి మొదటి ఆకు విశ్లేషణను అమలు చేయండి.",
  "history.empty.cta": "ఆకును విశ్లేషించండి",
  "history.confirmDelete": "ఈ స్కాన్‌ను తొలగించాలా?",
  "history.crop": "పంట",
  "history.pdfBtn": "PDF",
  "history.deleteAria": "స్కాన్‌ను తొలగించండి",
  "history.toast.loadFail": "చరిత్రను లోడ్ చేయడం సాధ్యం కాలేదు",
  "history.toast.deleted": "స్కాన్ తొలగించబడింది",
  "history.toast.deleteFail": "తొలగింపు విఫలమైంది",
  "history.toast.pdfFail": "నివేదికను డౌన్‌లోడ్ చేయడం సాధ్యం కాలేదు",
  "detail.back": "చరిత్రకు తిరిగి",
  "detail.loading": "నివేదిక లోడ్ అవుతోంది…",
  "detail.notFound": "స్కాన్ కనుగొనబడలేదు",
  "footer.tag": "ఒకే ఆకు ఫోటో నుండి మొక్కల వ్యాధి మరియు నీటి ఒత్తిడిని గుర్తించండి — సెన్సార్లు లేకుండా సులభంగా.",
  "footer.builtFor": "వీరి కోసం రూపొందించబడింది",
  "footer.role1": "పట్టణ తోటమాలులు",
  "footer.role2": "హాబీ రైతులు",
  "footer.role3": "కమ్యూనిటీ తోటలు",
  "footer.disclaimer": "గమనిక / నిరాకరణ",
  "footer.disclaimerText": "నివేదికలు సమాచార ప్రయోజనాల కొరకు మాత్రమే మరియు కనిపించే లక్షణాలపై ఆధారపడి ఉంటాయి. అవి ప్రయోగశాల పరీక్షలకు లేదా వృత్తిపరమైన సలహాకు ప్రత్యామ్నాయం కాదు.",
  "pdf.title": "స్మార్ట్‌ఫామ్ AI — మొక్క ఆరోగ్య నివేదిక",
  "pdf.generated": "రూపొందించబడింది:",
  "pdf.crop": "పంట:",
  "pdf.status": "స్థితి",
  "pdf.disease": "వ్యాధి",
  "pdf.confidence": "విశ్వాసం",
  "pdf.water": "నీటి ఒత్తిడి",
  "pdf.severity": "తీవ్రత అంచనా",
  "pdf.symptoms": "గుర్తించిన లక్షణాలు",
  "pdf.actions": "సిఫార్సు చేసిన చర్యలు",
  "pdf.preventive": "నివారణ చర్యలు",
  "pdf.notes": "వ్యాఖ్యలు",
  "pdf.footer": "స్మార్ట్‌ఫామ్ AI — మొక్కల ఆరోగ్య విశ్లేషణ సమాచారం కొరకు మాత్రమే, ఇది వృత్తిపరమైన వ్యవసాయ సలహాకు ప్రత్యామ్నాయం కాదు.",
  "ml.disease.Healthy": "ఆరోగ్యకరమైనది",
  "ml.disease.Late Blight": "లేట్ బ్లైట్ (ఆలస్యపు తెగులు)",
  "ml.disease.Early Blight": "ఎర్లీ బ్లైట్ (ముందస్తు తెగులు)",
  "ml.disease.Leaf Mold": "ఆకు బూజు (లీఫ్ మోల్డ్)",
  "ml.disease.Septoria Leaf Spot": "సెప్టోరియా ఆకు మచ్చ తెగులు",
  "ml.disease.Bacterial Spot": "బాక్టీరియల్ మచ్చల తెగులు",
  "ml.disease.Unhealthy (Unknown Type)": "అనారోగ్యకరమైనది (తెలియని రకం)",
  "ml.disease.Uncertain": "అనిశ్చితం",
  "ml.disease.Uncertain Result - Manual Verification Recommended": "అనిశ్చిత ఫలితం - మాన్యువల్ ధృవీకరణ సిఫార్సు చేయబడింది",
  "ml.disease.Analysis unavailable": "విశ్లేషణ అందుబాటులో లేదు",
  "ml.symptom.Brown spots": "గోధుమ రంగు మచ్చలు",
  "ml.symptom.Yellow patches": "పసుపు రంగు మచ్చలు",
  "ml.symptom.Lesions": "పుండ్లు / గాయాలు",
  "ml.symptom.Mold": "బూజు",
  "ml.symptom.Wilting": "వాడిపోవడం",
  "ml.symptom.Curling": "ఆకులు ముడుచుకోవడం",
  "ml.symptom.Discoloration": "రంగు మారడం",
  "ml.symptom.No visible disease symptoms": "కనిపించే వ్యాధి లక్షణాలు లేవు",
  "ml.symptom.Uniform green color": "ఏకరీతి ఆకుపచ్చ రంగు",
  "ml.symptom.No lesions or spots": "పుండ్లు లేదా మచ్చలు లేవు",
  "ml.symptom.Water-soaked lesions": "నీటితో తడిసిన గాయాలు",
  "ml.symptom.Circular lesions": "గుండ్రని గాయాలు",
  "ml.symptom.Powdery coating": "పొడి పూత",
  "ml.symptom.Small brown spots": "చిన్న గోధుమ రంగు మచ్చలు",
  "ml.symptom.Water-soaked spots": "నీటితో నానిన మచ్చలు",
  "ml.symptom.Insufficient evidence for classification": "వర్గీకరణకు తగిన ఆధారాలు లేవు",
  "ml.symptom.Analysis error": "విశ్లేషణ లోపం",
  "ml.symptom.Manual verification required": "మాన్యువల్ ధృవీకరణ అవసరం",
  "ml.symptom.Image analysis error occurred": "చిత్ర విశ్లేషణ లోపం సంభవించింది",
  "ml.symptom.AI vision service temporarily unavailable": "AI విజన్ సేవ తాత్కాలికంగా అందుబాటులో లేదు",
  "ml.symptom.Please try again later": "దయచేసి తర్వాత మళ్ళీ ప్రయత్నించండి",
  "ml.action.Maintain current watering schedule": "ప్రస్తుత నీటి షెడ్యూల్‌ను కొనసాగించండి",
  "ml.action.Monitor for any changes in leaf appearance": "ఆకు రూపురేఖలలో ఏవైనా మార్పులను గమనించండి",
  "ml.action.Maintain proper plant nutrition": "మొక్కకు సరైన పోషణను అందించండి",
  "ml.action.Remove and destroy affected plants immediately": "ప్రభావిత మొక్కలను వెంటనే తొలగించి నాశనం చేయండి",
  "ml.action.Apply fungicide containing chlorothalonil": "క్లోరోథలోనిల్ ఉన్న శిలీంద్ర సంహారిణిని వాడండి",
  "ml.action.Avoid working with plants when wet": "మొక్కలు తడిగా ఉన్నప్పుడు వాటిపై పని చేయవద్దు",
  "ml.action.Rotate crops to prevent recurrence": "వ్యాధి మళ్లీ రాకుండా పంట మార్పిడి చేయండి",
  "ml.action.Remove affected leaves to prevent spread": "వ్యాప్తిని అరికట్టడానికి ప్రభావిత ఆకులను తొలగించండి",
  "ml.action.Apply copper-based fungicide": "రాగి ఆధారిత శిలీంద్ర సంహారిణిని వర్తించండి",
  "ml.action.Improve air circulation around plants": "మొక్కల చుట్టూ గాలి ప్రసరణను మెరుగుపరచండి",
  "ml.action.Avoid overhead watering": "పై నుండి నీరు పోయడం నివారించండి",
  "ml.action.Improve air circulation significantly": "గాలి ప్రసరణను గణనీయంగా మెరుగుపరచండి",
  "ml.action.Reduce humidity around plants": "మొక్కల చుట్టూ తేమను తగ్గించండి",
  "ml.action.Remove affected lower leaves": "ప్రభావితమైన దిగువ ఆకులను తొలగించండి",
  "ml.action.Apply fungicide if severe": "తీవ్రంగా ఉంటే శిలీంద్ర సంహారిణిని వాడండి",
  "ml.action.Remove infected leaves immediately": "సోకిన ఆకులను వెంటనే తొలగించండి",
  "ml.action.Mulch to prevent splash dispersal": "చిమ్మడం ద్వారా వ్యాప్తిని అరికట్టడానికి మల్చింగ్ చేయండి",
  "ml.action.Remove infected plant material": "వ్యాధి సోకిన మొక్క భాగాలను తొలగించండి",
  "ml.action.Apply copper-based bactericide": "రాగి ఆధారిత బ్యాక్టీరియా సంహారిణిని వాడండి",
  "ml.action.Disinfect tools between uses": "వాడుకల మధ్య వ్యవసాయ పనిముట్లను క్రిమిసంహారక చేయండి",
  "ml.action.Inspect plant closely for additional symptoms": "అదనపు లక్షణాల కోసం మొక్కను నిశితంగా పరిశీలించండి",
  "ml.action.Consult agricultural extension service": "వ్యవసాయ విస్తరణ సేవలను లేదా నిపుణులను సంప్రదించండి",
  "ml.action.Isolate affected plant if possible": "వీలైతే ప్రభావిత మొక్కను వేరు చేయండి",
  "ml.action.Monitor for spread to other plants": "ఇతర మొక్కలకు వ్యాపించకుండా గమనించండి",
  "ml.action.Inspect plant closely for symptoms": "లక్షణాల కోసం మొక్కను నిశితంగా పరిశీలించండి",
  "ml.action.Consult agricultural extension": "వ్యవసాయ విస్తరణ కేంద్రాన్ని సంప్రదించండి",
  "ml.action.Monitor for changes in plant condition": "మొక్క పరిస్థితిలో మార్పులను గమనించండి",
  "ml.action.Check leaf for visible spots or discoloration": "కనిపించే మచ్చలు లేదా రంగు మారడం కోసం ఆకును తనిఖీ చేయండి",
  "ml.action.Ensure proper watering and sunlight": "సరైన నీరు మరియు సూర్యరశ్మిని నిర్ధారించుకోండి",
  "ml.action.Consult local agricultural extension if symptoms persist": "లక్షణాలు కొనసాగితే స్థానిక వ్యవసాయ నిపుణుడిని సంప్రదించండి",
  "ml.action.Try uploading the image again": "చిత్రాన్ని మళ్ళీ అప్‌లోడ్ చేయడానికి ప్రయత్నించండి",
  "ml.action.Increase watering frequency slightly": "నీరు పోసే ఫ్రీక్వెన్సీని కొద్దిగా పెంచండి",
  "ml.action.Check soil moisture regularly": "నేల తేమను క్రమం తప్పకుండా తనిఖీ చేయండి",
  "ml.action.Increase watering significantly": "నీటి పరిమాణాన్ని గణనీయంగా పెంచండి",
  "ml.action.Add mulch to retain moisture": "తేమను నిలుపుకోవడానికి మల్చ్ జోడించండి",
  "ml.action.Provide shade during peak heat": "ఎండ తీవ్రత ఎక్కువగా ఉన్నప్పుడు నీడను కల్పించండి",
  "ml.action.Immediate deep watering required": "వెంటనే లోతుగా నీరు పెట్టడం అవసరం",
  "ml.action.Consider plant recovery measures": "మొక్క కోలుకునే చర్యలను పరిగణించండి",
  "ml.action.Protect from direct sunlight": "ప్రత్యక్ష ఎండ నుండి రక్షించండి",
  "ml.preventive.Regularly inspect plants for early signs of disease": "వ్యాధి ముందస్తు లక్షణాల కోసం క్రమం తప్పకుండా మొక్కలను తనిఖీ చేయండి",
  "ml.preventive.Maintain proper spacing between plants": "మొక్కల మధ్య సరైన దూరం పాటించండి",
  "ml.preventive.Ensure good air circulation": "మంచి గాలి ప్రసరణ ఉండేలా చూసుకోండి",
  "ml.preventive.Use certified disease-free seeds": "ధృవీకరించబడిన వ్యాధి రహిత విత్తనాలను ఉపయోగించండి",
  "ml.preventive.Plant resistant varieties": "వ్యాధి నిరోధక రకాలను నాటండి",
  "ml.preventive.Ensure good drainage": "మంచి నీటి పారుదల సౌకర్యం ఉండేలా చూసుకోండి",
  "ml.preventive.Avoid overhead irrigation": "పైనుండి నీరు చిలకరించడం నివారించండి",
  "ml.preventive.Space plants properly for airflow": "గాలి ప్రసరణ కోసం మొక్కలను తగిన దూరంలో ఉంచండి",
  "ml.preventive.Water at base of plants, not leaves": "ఆకులపై కాకుండా మొక్కల మొదట్లో నీరు పోయండి",
  "ml.preventive.Remove plant debris regularly": "మొక్కల వ్యర్థాలను క్రమం తప్పకుండా తొలగించండి",
  "ml.preventive.Use disease-resistant varieties": "వ్యాధి నిరోధక రకాలను వాడండి",
  "ml.preventive.Avoid overcrowding": "మొక్కలను దగ్గర దగ్గరగా గుమిగూడకుండా చూడండి",
  "ml.preventive.Ensure good ventilation": "మంచి వెంటిలేషన్‌ను నిర్ధారించుకోండి",
  "ml.preventive.Water at soil level only": "నేల మట్టం వద్ద మాత్రమే నీరు పోయండి",
  "ml.preventive.Rotate crops annually": "ప్రతి సంవత్సరం పంట మార్పిడి చేయండి",
  "ml.preventive.Space plants properly": "మొక్కల మధ్య సరైన స్థలం ఉంచండి",
  "ml.preventive.Remove plant debris in fall": "రాలిన మొక్కల వ్యర్థాలను తొలగించండి",
  "ml.preventive.Use disease-free seeds and transplants": "వ్యాధి లేని విత్తనాలు మరియు నారును ఉపయోగించండి",
  "ml.preventive.Control insect vectors": "కీటక వాహకాలను నియంత్రించండి",
  "ml.preventive.Regular plant inspections": "క్రమబద్ధమైన మొక్కల తనిఖీ చేయండి",
  "ml.preventive.Maintain proper sanitation": "సరైన పరిశుభ్రతను పాటించండి",
  "ml.preventive.Quarantine new plants": "కొత్త మొక్కలను వేరుగా ఉంచి గమనించండి",
  "ml.preventive.Keep garden area clean": "తోట ప్రాంతాన్ని శుభ్రంగా ఉంచండి",
  "ml.preventive.Maintain proper plant care practices": "సరైన మొక్కల సంరక్షణ పద్ధతులను కొనసాగించండి",
  "ml.preventive.Avoid overhead watering to reduce fungal risk": "శిలీంధ్రాల ప్రమాదాన్ని తగ్గించడానికి పైనుండి నీరు పోయడం నివారించండి"
};

  const _ta = {
    'nav.analyze':'பகுப்பாய்வு','nav.history':'வரலாறு','nav.language':'மொழி',
    'hero.title1':'ஒரே இலையில் இருந்து','hero.title2':'தாவர நோயைக் கண்டறியுங்கள்.',
    'hero.cta':'இலையை பகுப்பாய்வு செய்',
    'uploader.analyzeBtn':'இலையை பகுப்பாய்வு செய்','uploader.analyzing':'பகுப்பாய்வு செய்கிறது…',
    'report.speak':'கேள்','report.stop':'நிறுத்து',
    'status.Healthy':'ஆரோக்கியம்','status.Unhealthy':'நோய்வாய்ப்பட்டது','status.Uncertain':'நிச்சயமற்றது',
    'history.title':'ஸ்கேன் வரலாறு','detail.back':'வரலாற்றுக்கு திரும்பு',
  };

  const _bn = {
    'nav.analyze':'বিশ্লেষণ','nav.history':'ইতিহাস','nav.language':'ভাষা',
    'hero.title1':'একটি পাতা থেকে','hero.title2':'গাছের রোগ চিহ্নিত করুন।',
    'hero.cta':'পাতা বিশ্লেষণ করুন',
    'uploader.analyzeBtn':'পাতা বিশ্লেষণ করুন','uploader.analyzing':'বিশ্লেষণ চলছে…',
    'report.speak':'শুনুন','report.stop':'থামান',
    'status.Healthy':'সুস্থ','status.Unhealthy':'অসুস্থ','status.Uncertain':'অনিশ্চিত',
    'history.title':'স্ক্যান ইতিহাস','detail.back':'ইতিহাসে ফিরুন',
  };

  const _mr = {
    'nav.analyze':'विश्लेषण','nav.history':'इतिहास','nav.language':'भाषा',
    'hero.title1':'एका पानावरून','hero.title2':'वनस्पतीचा रोग ओळखा.',
    'hero.cta':'पानाचे विश्लेषण करा',
    'uploader.analyzeBtn':'पानाचे विश्लेषण करा','uploader.analyzing':'विश्लेषण होत आहे…',
    'report.speak':'ऐका','report.stop':'थांबवा',
    'status.Healthy':'निरोगी','status.Unhealthy':'अनारोग्यकर','status.Uncertain':'अनिश्चित',
    'history.title':'स्कॅन इतिहास','detail.back':'इतिहासाकडे परत',
  };

  const _kn = {
    'nav.analyze':'ವಿಶ್ಲೇಷಣೆ','nav.history':'ಇತಿಹಾಸ','nav.language':'ಭಾಷೆ',
    'hero.title1':'ಒಂದು ಎಲೆಯಿಂದ','hero.title2':'ಸಸ್ಯ ರೋಗವನ್ನು ಪತ್ತೆಹಚ್ಚಿ.',
    'hero.cta':'ಎಲೆಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ',
    'uploader.analyzeBtn':'ಎಲೆಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ','uploader.analyzing':'ವಿಶ್ಲೇಷಣೆ ನಡೆಯುತ್ತಿದೆ…',
    'report.speak':'ಆಲಿಸಿ','report.stop':'ನಿಲ್ಲಿಸಿ',
    'status.Healthy':'ಆರೋಗ್ಯಕರ','status.Unhealthy':'ಅನಾರೋಗ್ಯಕರ','status.Uncertain':'ಅನಿಶ್ಚಿತ',
    'history.title':'ಸ್ಕ್ಯಾನ್ ಇತಿಹಾಸ','detail.back':'ಇತಿಹಾಸಕ್ಕೆ ಹಿಂದಿರುಗಿ',
  };

  const _gu = {
    'nav.analyze':'વિશ્લેષણ','nav.history':'ઇતિહાસ','nav.language':'ભાષા',
    'hero.title1':'એક પાંદડામાંથી','hero.title2':'છોડનો રોગ ઓળખો.',
    'hero.cta':'પાંદડાનું વિશ્લેષણ',
    'uploader.analyzeBtn':'પાંદડાનું વિશ્લેષણ','uploader.analyzing':'વિશ્લેષણ ચાલુ છે…',
    'report.speak':'સાંભળો','report.stop':'રોકો',
    'status.Healthy':'સ્વસ્થ','status.Unhealthy':'અસ્વસ્થ','status.Uncertain':'અનિશ્ચિત',
    'history.title':'સ્કેન ઇતિહાસ','detail.back':'ઇતિહાસ પર પાછા',
  };

  const TRANSLATIONS = { en:_en, hi:_hi, te:_te, ta:_ta, bn:_bn, mr:_mr, kn:_kn, gu:_gu };

  // Build reverse lookup index for translating reports
  const _REVERSE_INDEX = {};
  [_en, _hi, _te].forEach(dict => {
    Object.keys(dict).forEach(k => {
      const val = dict[k];
      if (typeof val === 'string' && val.trim()) {
        _REVERSE_INDEX[val.trim().toLowerCase()] = k;
      }
    });
  });

  let _currentLang = DEFAULT_LANG;

  function t(key, defaultVal) {
    const dict = TRANSLATIONS[_currentLang] || _en;
    if (key in dict) return dict[key];
    if (key in _en) return _en[key];
    return defaultVal !== undefined ? defaultVal : key;
  }

  function getLang() { return _currentLang; }

  function getLangMeta() { return LANGUAGES.find(l => l.code === _currentLang) || LANGUAGES[0]; }

  function translateItem(text, prefix, targetLang) {
    if (!text || typeof text !== 'string') return text;
    const clean = text.trim().replace(/[.,!?:;]+$/, '').trim();
    const directKey = prefix + '.' + text.trim();
    const cleanKey = prefix + '.' + clean;

    if (directKey in _en) {
      const val = (TRANSLATIONS[targetLang] && TRANSLATIONS[targetLang][directKey]) || _en[directKey];
      if (val) return val;
    }
    if (cleanKey in _en) {
      const val = (TRANSLATIONS[targetLang] && TRANSLATIONS[targetLang][cleanKey]) || _en[cleanKey];
      if (val) return val;
    }

    const lower = text.trim().toLowerCase();
    const lowerClean = clean.toLowerCase();

    let key = _REVERSE_INDEX[lower] || _REVERSE_INDEX[lowerClean];
    if (key && key.startsWith(prefix)) {
      const val = (TRANSLATIONS[targetLang] && TRANSLATIONS[targetLang][key]) || _en[key];
      if (val) return val;
    }

    // Search across dictionaries
    for (const l of ['en', 'hi', 'te', 'ta', 'bn', 'mr', 'kn', 'gu']) {
      const d = TRANSLATIONS[l] || {};
      for (const k in d) {
        if (k.startsWith(prefix)) {
          const dv = d[k].trim().toLowerCase();
          const dvClean = dv.replace(/[.,!?:;]+$/, '').trim();
          if (dv === lower || dvClean === lowerClean) {
            const val = (TRANSLATIONS[targetLang] && TRANSLATIONS[targetLang][k]) || _en[k];
            if (val) return val;
          }
        }
      }
    }
    return text;
  }

  function translateSeverity(severity, disease, conf, targetLang) {
    if (!severity) return severity;
    const s = severity.toLowerCase();
    if (targetLang === 'en') {
      if (s.includes('healthy') || severity.includes('स्वस्थ') || severity.includes('ఆరోగ్య')) return 'Plant appears healthy with no obvious signs of disease.';
      if (s.includes('late blight') || severity.includes('पछेती') || severity.includes('లేట్ బ్లైట్') || severity.includes('ఆలస్యపు')) return 'Late blight detected with ' + conf + '% confidence. Serious fungal disease.';
      if (s.includes('early blight') || severity.includes('अगेती') || severity.includes('ఎర్లీ బ్లైట్') || severity.includes('ముందస్తు')) return 'Early blight detected with ' + conf + '% confidence. Fungal infection likely.';
      if (s.includes('leaf mold') || severity.includes('मोल्ड') || severity.includes('ఆకు బూజు')) return 'Leaf mold detected with ' + conf + '% confidence. Fungal infection present.';
      if (s.includes('septoria') || severity.includes('सेप्टोरिया') || severity.includes('సెప్టోరియా')) return 'Septoria leaf spot detected with ' + conf + '% confidence. Common fungal disease.';
      if (s.includes('bacterial') || severity.includes('जीवाणु') || severity.includes('बैक्टीरियल') || severity.includes('బాక్టీరియల్')) return 'Bacterial spot detected with ' + conf + '% confidence. Bacterial infection.';
      if (s.includes('uncertain') || severity.includes('अनिश्चित') || severity.includes('అనిశ్చిత')) return 'Uncertain result with ' + conf + '% confidence. Manual verification recommended.';
      if (s.includes('unable') || severity.includes('असमर्थ') || severity.includes('విశ్లేషించలేకపోయాము')) return 'Unable to analyze leaf image due to service limitations.';
      if (severity.includes('స్పష్టంగా లేదు') || severity.includes('स्पष्ट नहीं')) return 'Disease detected with ' + conf + '% confidence. Specific type unclear.';
      return severity;
    }
    if (targetLang === 'hi') {
      if (s.includes('healthy') || severity.includes('स्वस्थ') || severity.includes('ఆరోగ్య')) return 'पौधा स्वस्थ दिखता है और बीमारी का कोई स्पष्ट संकेत नहीं है।';
      if (s.includes('late blight') || severity.includes('पछेती') || severity.includes('లేట్ బ్లైట్') || severity.includes('ఆలస్యపు')) return 'पछेती झुलसा ' + conf + '% विश्वास के साथ पहचाना गया। गंभीर फंगल रोग।';
      if (s.includes('early blight') || severity.includes('अगेती') || severity.includes('ఎర్లీ బ్లైట్') || severity.includes('ముందస్తు')) return 'अगेती झुलसा ' + conf + '% विश्वास के साथ पहचाना गया। फंगल संक्रमण की संभावना।';
      if (s.includes('leaf mold') || severity.includes('मोल्ड') || severity.includes('ఆకు బూజు')) return 'लीफ मोल्ड ' + conf + '% विश्वास के साथ पहचाना गया। फंगल संक्रमण मौजूद है।';
      if (s.includes('septoria') || severity.includes('सेप्टोरिया') || severity.includes('సెప్టోరియా')) return 'सेप्टोरिया लीफ स्पॉट ' + conf + '% विश्वास के साथ पहचाना गया। सामान्य फंगल रोग।';
      if (s.includes('bacterial') || severity.includes('जीवाणु') || severity.includes('बैक्टीरियल') || severity.includes('బాక్టీరియల్')) return 'बैक्टीरियल स्पॉट ' + conf + '% विश्वास के साथ पहचाना गया। जीवाणु संक्रमण।';
      if (s.includes('uncertain') || severity.includes('अनिश्चित') || severity.includes('అనిశ్చిత')) return 'अनिश्चित परिणाम ' + conf + '% विश्वास के साथ। मैन्युअल सत्यापन अनुशंसित।';
      if (s.includes('unable') || severity.includes('असमर्थ') || severity.includes('విశ్లేషించలేకపోయాము')) return 'सेवा सीमाओं के कारण पत्ती की छवि का विश्लेषण करने में असमर्थ।';
      return 'रोग ' + conf + '% विश्वास के साथ पहचाना गया। विशिष्ट प्रकार स्पष्ट नहीं है।';
    }
    if (targetLang === 'te') {
      if (s.includes('healthy') || severity.includes('स्वस्थ') || severity.includes('ఆరోగ్య')) return 'మొక్క ఆరోగ్యంగా కనిపిస్తోంది మరియు ఎటువంటి వ్యాధి లక్షణాలు లేవు.';
      if (s.includes('late blight') || severity.includes('पछेती') || severity.includes('లేట్ బ్లైట్') || severity.includes('ఆలస్యపు')) return 'లేట్ బ్లైట్ ' + conf + '% విశ్వాసంతో గుర్తించబడింది. తీవ్రమైన ఫంగల్ వ్యాధి.';
      if (s.includes('early blight') || severity.includes('अगेती') || severity.includes('ఎర్లీ బ్లైట్') || severity.includes('ముందస్తు')) return 'ఎర్లీ బ్లైట్ ' + conf + '% విశ్వాసంతో గుర్తించబడింది. ఫంగల్ ఇన్ఫెక్షన్ సంభావ్యత.';
      if (s.includes('leaf mold') || severity.includes('मोल्ड') || severity.includes('ఆకు బూజు')) return 'ఆకు బూజు తెగులు ' + conf + '% విశ్వాసంతో గుర్తించబడింది. ఫంగల్ ఇన్ఫెక్షన్ ఉంది.';
      if (s.includes('septoria') || severity.includes('सेप्टोरिया') || severity.includes('సెప్టోరియా')) return 'సెప్టోరియా ఆకు మచ్చ తెగులు ' + conf + '% విశ్వాసంతో గుర్తించబడింది. సాధారణ ఫంగల్ వ్యాధి.';
      if (s.includes('bacterial') || severity.includes('जीवाणु') || severity.includes('बैक्टीरियल') || severity.includes('బాక్టీరియల్')) return 'బాక్టీరియల్ స్పాట్ ' + conf + '% విశ్వాసంతో గుర్తించబడింది. బ్యాక్టీరియల్ ఇన్ఫెక్షన్.';
      if (s.includes('uncertain') || severity.includes('अनिश्चित') || severity.includes('అనిశ్చిత')) return 'అనిశ్చిత ఫలితం ' + conf + '% విశ్వాసంతో. మాన్యువల్ ధృవీకరణ సిఫార్సు చేయబడింది.';
      if (s.includes('unable') || severity.includes('असमर्थ') || severity.includes('విశ్లేషించలేకపోయాము')) return 'సేవా పరిమితుల కారణంగా ఆకు చిత్రాన్ని విశ్లేషించలేకపోయాము.';
      return 'వ్యాధి ' + conf + '% విశ్వాసంతో గుర్తించబడింది. నిర్దిష్ట రకం అస్పష్టంగా ఉంది.';
    }
    return severity;
  }

  function translateNotes(notes, health, disease, conf, stress, targetLang) {
    if (!notes) return notes;
    const diseaseTrans = translateItem(disease, 'ml.disease', targetLang);
    const targetDict = TRANSLATIONS[targetLang] || _en;
    const healthTrans = (targetDict && targetDict['status.' + health]) || _en['status.' + health] || health;
    const stressTrans = (targetDict && targetDict['stress.' + stress]) || _en['stress.' + stress] || stress;
    if (targetLang === 'hi') {
      if (notes.toLowerCase().includes('two-stage') || notes.includes('विश्लेषण') || notes.includes('విశ్లేషణ')) {
        return 'दो-चरणीय विश्लेषण: स्वास्थ्य=' + healthTrans + ', रोग=' + diseaseTrans + ', विश्वास=' + conf + '%, जल तनाव=' + stressTrans + '।';
      }
      if (notes.toLowerCase().includes('issues') || notes.toLowerCase().includes('fallback') || notes.includes('अस्थायी') || notes.includes('తాత్కాలికంగా')) {
        return 'एआई विश्लेषण सेवा वर्तमान में समस्याओं का सामना कर रही है। यह एक वैकल्पिक प्रतिक्रिया है। कृपया बाद में छवि को पुनः अपलोड करें।';
      }
      if (notes.toLowerCase().includes('failed') || notes.includes('विफल') || notes.includes('విఫలమైంది')) {
        return 'छवि विश्लेषण विफल रहा। मैन्युअल सत्यापन अनुशंसित।';
      }
      return notes;
    }
    if (targetLang === 'te') {
      if (notes.toLowerCase().includes('two-stage') || notes.includes('विश्लेषण') || notes.includes('విశ్లేషణ')) {
        return 'రెండు-దశల విశ్లేషణ: ఆరోగ్యం=' + healthTrans + ', వ్యాధి=' + diseaseTrans + ', విశ్వాసం=' + conf + '%, నీటి ఒత్తిడి=' + stressTrans + '.';
      }
      if (notes.toLowerCase().includes('issues') || notes.toLowerCase().includes('fallback') || notes.includes('అస్థायी') || notes.includes('తాత్కాలికంగా')) {
        return 'AI విశ్లేషణ సేవ ప్రస్తుతం సమస్యలను ఎదుర్కొంటోంది. ఇది ప్రత్యామ్నాయ ప్రతిస్పందన. దయచేసి తర్వాత మళ్ళీ చిత్రాన్ని అప్‌లోడ్ చేయడానికి ప్రయత్నించండి.';
      }
      if (notes.toLowerCase().includes('failed') || notes.includes('विफल') || notes.includes('విఫలమైంది')) {
        return 'చిత్ర విశ్లేషణ విఫలమైంది. మాన్యువల్ ధృవీకరణ సిఫార్సు చేయబడింది.';
      }
      return notes;
    }
    if (targetLang === 'en') {
      if (notes.toLowerCase().includes('two-stage') || notes.includes('विश्लेषण') || notes.includes('విశ్లేషణ')) {
        const enDisease = translateItem(disease, 'ml.disease', 'en');
        return 'Two-stage analysis: Health=' + (_en['status.' + health] || health) + ', Disease=' + enDisease + ', Confidence=' + conf + '%, Water Stress=' + (_en['stress.' + stress] || stress) + '.';
      }
      if (notes.includes('अस्थायी') || notes.includes('తాత్కాలికంగా')) {
        return 'AI analysis service is currently experiencing issues. This is a fallback response. Please try uploading the image again later.';
      }
      if (notes.includes('विफल') || notes.includes('విఫలమైంది')) {
        return 'Image analysis failed. Manual verification recommended.';
      }
      return notes;
    }
    return notes;
  }

  function translateReport(report, targetLang) {
    if (!report || !targetLang) return report;
    const res = Object.assign({}, report);
    const health = res.plant_health_status || 'Uncertain';
    const stress = res.water_stress_level || 'Low';
    const disease = res.predicted_disease || 'Unknown';
    const conf = res.confidence_score || 0;

    res.predicted_disease = translateItem(disease, 'ml.disease', targetLang);
    res.detected_symptoms = (res.detected_symptoms || []).map(s => translateItem(s, 'ml.symptom', targetLang));
    res.recommended_actions = (res.recommended_actions || []).map(a => translateItem(a, 'ml.action', targetLang));
    res.preventive_measures = (res.preventive_measures || []).map(p => translateItem(p, 'ml.preventive', targetLang));
    res.severity_assessment = translateSeverity(res.severity_assessment, disease, conf, targetLang);
    res.notes = translateNotes(res.notes, health, disease, conf, stress, targetLang);
    return res;
  }

  function applyTranslations() {
    // data-i18n text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });
    // data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = t(key);
    });
    // data-i18n-aria
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria');
      el.setAttribute('aria-label', t(key));
    });
    // data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = t(key);
    });
    // data-i18n-alt
    document.querySelectorAll('[data-i18n-alt]').forEach(el => {
      const key = el.getAttribute('data-i18n-alt');
      el.alt = t(key);
    });

    // Update document title dynamically
    const p = window.location.pathname;
    if (p === '/history') {
      document.title = t('page.title.history');
    } else if (p.startsWith('/scan/')) {
      document.title = t('page.title.detail');
    } else {
      document.title = t('page.title.home');
    }

    // Update HTML root lang attribute
    const htmlRoot = document.getElementById('html-root') || document.documentElement;
    if (htmlRoot) htmlRoot.lang = _currentLang;

    // Update header lang display
    const meta = getLangMeta();
    const codeEl = document.getElementById('lang-code-display');
    const nativeEl = document.getElementById('lang-native-display');
    if (codeEl) codeEl.textContent = _currentLang.toUpperCase();
    if (nativeEl) nativeEl.textContent = meta.native;

    // Mark active item in dropdown
    document.querySelectorAll('.sf-lang-item').forEach(el => {
      el.classList.toggle('active-lang', el.dataset.lang === _currentLang);
    });
  }

  function setLanguage(code) {
    if (!TRANSLATIONS[code]) return;
    _currentLang = code;
    try { localStorage.setItem(STORAGE_KEY, code); } catch(e) {}
    applyTranslations();
    // Fire custom event so all pages, components, reports and voice can react
    window.dispatchEvent(new CustomEvent('sf:languageChanged', { detail: { lang: code } }));
  }

  function init() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && TRANSLATIONS[stored]) _currentLang = stored;
    } catch(e) {}
    applyTranslations();

    // Dropdown click handlers
    document.querySelectorAll('.sf-lang-item').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        setLanguage(el.dataset.lang);
      });
    });
  }

  // Expose globally
  window.i18n = {
    t,
    getLang,
    getLangMeta,
    setLanguage,
    applyTranslations,
    translateReport,
    translateItem,
    LANGUAGES
  };

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(window);
