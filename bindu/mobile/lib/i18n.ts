import { useProfile } from "@/stores/profile";

/**
 * Interface strings in English and Nepali. `ne` is typed against `en`, so a missing translation fails the typecheck.
 * Lesson content comes from the curriculum and AI answers come from the model; those are not part of this table.
 */
const en = {
  "common.close": "Close",
  "common.tryAgain": "Try again",
  "common.error": "Something went wrong",
  "common.cancel": "Cancel",
  "common.unexpected": "Something unexpected happened. Please try again.",

  "tabs.home": "Home",
  "tabs.explore": "Explore",
  "tabs.journey": "My Journey",
  "tabs.learn": "Learn",

  "home.welcome": "Welcome, {name}",
  "home.welcomeGuest": "Welcome to BINDU",
  "home.streak": "{n} day streak",
  "home.xpLevel": "{xp} XP · Level {level}",
  "home.whatToDo": "What would you like to do?",
  "home.explore": "Explore with AI",
  "home.exploreSub": "Photo → culture",
  "home.learn": "Learn Nepali",
  "home.learnSub": "Travel phrases",
  "home.ask": "Ask BINDU",
  "home.askSub": "Culture Q&A",
  "home.continue": "Continue learning",
  "home.allDone": "All current lessons complete. More are on the way.",
  "home.recent": "Recent discoveries",
  "home.profile": "Profile and settings",

  "learn.title": "Learn Nepali",
  "learn.cleared": "{done}/{total} lessons cleared",
  "learn.unit": "Unit {n} · {name}",
  "learn.unitProgress": "{done}/{total} lessons complete",
  "learn.nextHeart": "Next heart in about {h}h",
  "learn.review": "tap to review",
  "learn.locked": "locked",

  "lesson.check": "Check",
  "lesson.continue": "Continue",
  "lesson.correct": "Correct!",
  "lesson.wrong": "Not quite. Answer: {answer}",
  "lesson.complete": "Lesson complete!",
  "lesson.noHearts": "Out of hearts",
  "lesson.noHeartsBody": "A heart refills about every 4 hours. Next one in roughly {h}h.",
  "lesson.backToLessons": "Back to lessons",
  "lesson.question": "Question {n} of {total}",
  "lesson.notFound": "Lesson not found.",
  "lesson.hearQuestion": "Listen to the question again",
  "lesson.hearOption": "Listen to {option}",
  "lesson.hearAnswer": "Hear the answer",
  "lesson.hearSentence": "Listen to your sentence",
  "lesson.tapToHear": "Tap a word to hear it.",
  "lesson.audioUnavailable": "Nepali audio isn't available right now. It needs a connection to the BINDU server, or a Nepali voice installed on this device.",

  "journey.title": "My Journey",
  "journey.saved": "Saved discoveries",
  "journey.savedHint": "Landmarks you photographed and saved",
  "journey.nothingSaved": "Nothing saved yet",
  "journey.nothingSavedBody": "Photograph a landmark in Explore and tap Save to keep it here.",
  "journey.card": "Card",
  "journey.remove": "Remove",

  "profile.title": "Profile",
  "profile.guest": "Guest explorer",
  "profile.guestNote": "Guest mode · progress is saved on this device only",
  "profile.signedInAs": "Signed in as {email}",
  "profile.level": "Level",
  "profile.streak": "Streak",
  "profile.lessons": "Lessons",
  "profile.savedStat": "Saved",
  "profile.account": "Account",
  "profile.syncNow": "Sync now",
  "profile.synced": "Synced: {d} discoveries.",
  "profile.signOut": "Sign out",
  "profile.signIn": "Sign in or create account",
  "profile.about": "About you",
  "profile.name": "Your name",
  "profile.interests": "Interests",
  "profile.ifaceLang": "Interface language",
  "profile.nepaliLevel": "Nepali level",
  "profile.privacy": "Privacy",
  "profile.privacyBody":
    "Photos you analyze are sent to the BINDU server and the AI provider to generate an answer. BINDU does not keep them unless you save a discovery, and even then only the text result is stored on this device.",
  "profile.reset": "Reset all local data",
  "profile.deleteAccount": "Delete my account",
  "profile.deleteTitle": "Delete your account permanently?",
  "profile.deleteBody":
    "This permanently deletes your account and everything synced to it: lesson progress and saved discoveries. It can't be undone. Data on this device is kept.",
  "profile.deleteConfirm": "Delete account",
  "profile.deleteFailed": "Your account couldn't be deleted. Check your connection and try again.",
  "profile.deleted": "Your account was deleted.",

  "onboarding.tagline": "Explore Nepal. Understand its culture. Learn its language.",
  "onboarding.callYou": "What should we call you?",
  "onboarding.optional": "Optional. You can change it any time in Profile.",
  "onboarding.yourName": "Your name",
  "onboarding.level": "Your Nepali level",
  "onboarding.interestsQ": "What are you into?",
  "onboarding.pickAny": "Pick any that apply.",
  "onboarding.start": "Start exploring",

  "auth.signIn": "Sign in",
  "auth.create": "Create account",
  "auth.blurb": "Your account keeps your name, lessons, XP and streak safe, and in sync across devices.",
  "auth.notConfigured": "Accounts aren't enabled in this build (no Supabase project configured). Set EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY to turn them on.",
  "auth.email": "Email",
  "auth.password": "Password (8+ characters)",
  "auth.newHere": "New here? Create an account",
  "auth.haveAccount": "Have an account? Sign in",
  "auth.forgot": "Forgot your password?",
  "auth.resetSent": "If that email has an account, a link to reset the password is on its way.",
  "auth.resetNeedsEmail": "Enter your email above first, then tap “Forgot your password?”.",
  "auth.invalidEmail": "Enter a valid email address.",
  "auth.shortPassword": "Use a password with at least 8 characters.",
  "auth.name": "Your name",
  "profile.signOutFailed": "Couldn't save your progress to your account, so you were not signed out. Connect to the internet and try again.",
  "auth.confirm": "Confirm password",
  "auth.nameRequired": "Enter your name.",
  "auth.mismatch": "The two passwords don't match.",
  "welcome.blurb": "Sign in to continue your lessons, or create a free account to get started.",
  "auth.confirmNotice": "Account created. Check your email and tap the confirmation link, then sign in here.",

  "explore.title": "Explore with AI",
  "explore.subtitle": "Photograph a temple, carving, dish or craft and learn what you're looking at.",
  "explore.takePhoto": "Take a photo",
  "explore.gallery": "Choose from gallery",
  "explore.analyze": "Analyze photo",
  "explore.differentPhoto": "Choose a different photo",
  "explore.looking": "Looking closely…",
  "explore.save": "Save discovery",
  "explore.saved": "Saved to My Journey ✓",
  "explore.newPhoto": "New photo",
  "explore.followUp": "Ask a follow-up",
  "explore.ask": "Ask",

  "assistant.title": "Ask BINDU",
  "assistant.intro": "Ask about etiquette, food, festivals, language or getting around. I won't guess prices or opening hours.",
  "assistant.placeholder": "Ask a question",
  "assistant.send": "Send",

  "notFound.title": "This page doesn't exist",
  "notFound.home": "Go to Home",
  "crash.title": "BINDU hit a problem",
  "crash.body": "Something broke on this screen. Your saved data is safe.",
  "crash.retry": "Try again",

  // Option labels shown in chips (the underlying value stays English).
  "opt.Beginner": "Beginner",
  "opt.Intermediate": "Intermediate",
  "opt.Advanced": "Advanced",
  "opt.Culture & heritage": "Culture & heritage",
  "opt.Local food": "Local food",
  "opt.Nature & trekking": "Nature & trekking",
  "opt.Temples & monasteries": "Temples & monasteries",
  "opt.Markets & crafts": "Markets & crafts",
  "opt.Off the beaten path": "Off the beaten path",
} as const;

export type I18nKey = keyof typeof en;

const ne: Record<I18nKey, string> = {
  "common.close": "बन्द गर्नुहोस्",
  "common.tryAgain": "फेरि प्रयास गर्नुहोस्",
  "common.error": "केही गडबड भयो",
  "common.cancel": "रद्द गर्नुहोस्",
  "common.unexpected": "केही अप्रत्याशित भयो। कृपया फेरि प्रयास गर्नुहोस्।",

  "tabs.home": "गृह",
  "tabs.explore": "अन्वेषण",
  "tabs.journey": "मेरो यात्रा",
  "tabs.learn": "सिक्नुहोस्",

  "home.welcome": "स्वागत छ, {name}",
  "home.welcomeGuest": "BINDU मा स्वागत छ",
  "home.streak": "{n} दिनको स्ट्रिक",
  "home.xpLevel": "{xp} XP · तह {level}",
  "home.whatToDo": "तपाईं के गर्न चाहनुहुन्छ?",
  "home.explore": "AI सँग अन्वेषण",
  "home.exploreSub": "फोटो → संस्कृति",
  "home.learn": "नेपाली सिक्नुहोस्",
  "home.learnSub": "यात्रा वाक्यांश",
  "home.ask": "BINDU लाई सोध्नुहोस्",
  "home.askSub": "संस्कृति प्रश्नोत्तर",
  "home.continue": "सिकाइ जारी राख्नुहोस्",
  "home.allDone": "हालका सबै पाठ पूरा भए। थप पाठ चाँडै आउँदैछन्।",
  "home.recent": "हालका खोजहरू",
  "home.profile": "प्रोफाइल र सेटिङ",

  "learn.title": "नेपाली सिक्नुहोस्",
  "learn.cleared": "{done}/{total} पाठ पूरा भए",
  "learn.unit": "एकाइ {n} · {name}",
  "learn.unitProgress": "{done}/{total} पाठ पूरा",
  "learn.nextHeart": "अर्को मुटु करिब {h} घण्टामा",
  "learn.review": "दोहोर्याउन थिच्नुहोस्",
  "learn.locked": "बन्द",

  "lesson.check": "जाँच गर्नुहोस्",
  "lesson.continue": "जारी राख्नुहोस्",
  "lesson.correct": "सही!",
  "lesson.wrong": "ठीक भएन। उत्तर: {answer}",
  "lesson.complete": "पाठ पूरा भयो!",
  "lesson.noHearts": "मुटु सकियो",
  "lesson.noHeartsBody": "एउटा मुटु करिब हरेक ४ घण्टामा फर्कन्छ। अर्को करिब {h} घण्टामा आउँछ।",
  "lesson.backToLessons": "पाठहरूमा फर्कनुहोस्",
  "lesson.question": "प्रश्न {n} / {total}",
  "lesson.notFound": "पाठ भेटिएन।",
  "lesson.hearQuestion": "प्रश्न फेरि सुन्नुहोस्",
  "lesson.hearOption": "{option} सुन्नुहोस्",
  "lesson.hearAnswer": "उत्तर सुन्नुहोस्",
  "lesson.hearSentence": "तपाईंको वाक्य सुन्नुहोस्",
  "lesson.tapToHear": "शब्द सुन्न त्यसमा थिच्नुहोस्।",
  "lesson.audioUnavailable": "नेपाली अडियो अहिले उपलब्ध छैन। यसका लागि BINDU सर्भरसँग जडान वा यो उपकरणमा नेपाली आवाज चाहिन्छ।",

  "journey.title": "मेरो यात्रा",
  "journey.saved": "सुरक्षित खोजहरू",
  "journey.savedHint": "तपाईंले खिचेर सुरक्षित गरेका स्थलहरू",
  "journey.nothingSaved": "अहिलेसम्म केही सुरक्षित छैन",
  "journey.nothingSavedBody": "अन्वेषणमा कुनै स्थलको फोटो खिचेर ‘सुरक्षित गर्नुहोस्’ थिच्नुहोस्।",
  "journey.card": "कार्ड",
  "journey.remove": "हटाउनुहोस्",

  "profile.title": "प्रोफाइल",
  "profile.guest": "अतिथि अन्वेषक",
  "profile.guestNote": "अतिथि मोड · प्रगति यही उपकरणमा मात्र सुरक्षित हुन्छ",
  "profile.signedInAs": "{email} बाट साइन इन गरिएको",
  "profile.level": "तह",
  "profile.streak": "स्ट्रिक",
  "profile.lessons": "पाठ",
  "profile.savedStat": "सुरक्षित",
  "profile.account": "खाता",
  "profile.syncNow": "अहिले सिंक गर्नुहोस्",
  "profile.synced": "सिंक भयो: {d} खोज।",
  "profile.signOut": "साइन आउट",
  "profile.signIn": "साइन इन वा खाता बनाउनुहोस्",
  "profile.about": "तपाईंको बारेमा",
  "profile.name": "तपाईंको नाम",
  "profile.interests": "रुचिहरू",
  "profile.ifaceLang": "इन्टरफेस भाषा",
  "profile.nepaliLevel": "नेपालीको तह",
  "profile.privacy": "गोपनीयता",
  "profile.privacyBody":
    "तपाईंले विश्लेषण गर्ने फोटोहरू उत्तर तयार गर्न BINDU सर्भर र AI प्रदायकलाई पठाइन्छन्। तपाईंले खोज सुरक्षित नगरेसम्म BINDU ले ती राख्दैन, र सुरक्षित गर्दा पनि पाठ नतिजा मात्र यही उपकरणमा राखिन्छ।",
  "profile.reset": "सबै स्थानीय डेटा मेटाउनुहोस्",
  "profile.deleteAccount": "मेरो खाता मेटाउनुहोस्",
  "profile.deleteTitle": "खाता स्थायी रूपमा मेटाउने?",
  "profile.deleteBody":
    "यसले तपाईंको खाता र त्यसमा सिंक भएका सबै कुरा (पाठको प्रगति र सुरक्षित खोज) स्थायी रूपमा मेटाउँछ। यो फिर्ता गर्न सकिँदैन। यो उपकरणमा रहेको डेटा रहिरहन्छ।",
  "profile.deleteConfirm": "खाता मेटाउनुहोस्",
  "profile.deleteFailed": "तपाईंको खाता मेटाउन सकिएन। इन्टरनेट जाँचेर फेरि प्रयास गर्नुहोस्।",
  "profile.deleted": "तपाईंको खाता मेटाइयो।",

  "onboarding.tagline": "नेपाल अन्वेषण गर्नुहोस्। यसको संस्कृति बुझ्नुहोस्। यसको भाषा सिक्नुहोस्।",
  "onboarding.callYou": "हामीले तपाईंलाई के भनेर बोलाऔं?",
  "onboarding.optional": "ऐच्छिक। तपाईं यसलाई प्रोफाइलमा जुनसुकै बेला बदल्न सक्नुहुन्छ।",
  "onboarding.yourName": "तपाईंको नाम",
  "onboarding.level": "तपाईंको नेपालीको तह",
  "onboarding.interestsQ": "तपाईंलाई केमा रुचि छ?",
  "onboarding.pickAny": "मन परेका जति छान्नुहोस्।",
  "onboarding.start": "सुरु गर्नुहोस्",

  "auth.signIn": "साइन इन",
  "auth.create": "खाता बनाउनुहोस्",
  "auth.blurb": "खाताले तपाईंको नाम, पाठ, XP र स्ट्रिक सुरक्षित राख्छ र विभिन्न उपकरणमा सिंक गर्छ।",
  "auth.notConfigured": "यो संस्करणमा खाता सुविधा खुला गरिएको छैन (Supabase प्रोजेक्ट सेट गरिएको छैन)। खोल्न EXPO_PUBLIC_SUPABASE_URL र EXPO_PUBLIC_SUPABASE_ANON_KEY सेट गर्नुहोस्।",
  "auth.email": "इमेल",
  "auth.password": "पासवर्ड (कम्तीमा ८ अक्षर)",
  "auth.newHere": "नयाँ हुनुहुन्छ? खाता बनाउनुहोस्",
  "auth.haveAccount": "खाता छ? साइन इन गर्नुहोस्",
  "auth.forgot": "पासवर्ड बिर्सनुभयो?",
  "auth.resetSent": "त्यो इमेलमा खाता छ भने पासवर्ड पुनःसेट गर्ने लिङ्क पठाइँदैछ।",
  "auth.resetNeedsEmail": "पहिले माथि इमेल हाल्नुहोस्, त्यसपछि ‘पासवर्ड बिर्सनुभयो?’ थिच्नुहोस्।",
  "auth.invalidEmail": "मान्य इमेल ठेगाना हाल्नुहोस्।",
  "auth.shortPassword": "कम्तीमा ८ अक्षरको पासवर्ड प्रयोग गर्नुहोस्।",
  "auth.name": "तपाईंको नाम",
  "profile.signOutFailed": "तपाईंको प्रगति खातामा सुरक्षित गर्न सकिएन, त्यसैले साइन आउट गरिएन। इन्टरनेटमा जडान भएर फेरि प्रयास गर्नुहोस्।",
  "auth.confirm": "पासवर्ड पुष्टि गर्नुहोस्",
  "auth.nameRequired": "आफ्नो नाम हाल्नुहोस्।",
  "auth.mismatch": "दुई पासवर्ड मिलेनन्।",
  "welcome.blurb": "पाठ जारी राख्न साइन इन गर्नुहोस्, वा सुरु गर्न निःशुल्क खाता बनाउनुहोस्।",
  "auth.confirmNotice": "खाता बनाइयो। इमेल हेरेर पुष्टि गर्ने लिङ्कमा थिच्नुहोस्, अनि यहाँ साइन इन गर्नुहोस्।",

  "explore.title": "AI सँग अन्वेषण",
  "explore.subtitle": "मन्दिर, कुँदिएको कला, परिकार वा हस्तकलाको फोटो खिच्नुहोस् र आफूले हेरिरहेको कुरा बुझ्नुहोस्।",
  "explore.takePhoto": "फोटो खिच्नुहोस्",
  "explore.gallery": "ग्यालरीबाट छान्नुहोस्",
  "explore.analyze": "फोटो विश्लेषण गर्नुहोस्",
  "explore.differentPhoto": "अर्को फोटो छान्नुहोस्",
  "explore.looking": "ध्यानपूर्वक हेर्दैछ…",
  "explore.save": "खोज सुरक्षित गर्नुहोस्",
  "explore.saved": "मेरो यात्रामा सुरक्षित गरियो ✓",
  "explore.newPhoto": "नयाँ फोटो",
  "explore.followUp": "थप प्रश्न सोध्नुहोस्",
  "explore.ask": "सोध्नुहोस्",

  "assistant.title": "BINDU लाई सोध्नुहोस्",
  "assistant.intro": "शिष्टाचार, खाना, चाडपर्व, भाषा वा यात्राबारे सोध्नुहोस्। म मूल्य वा खुल्ने समय अनुमान गर्दिनँ।",
  "assistant.placeholder": "प्रश्न सोध्नुहोस्",
  "assistant.send": "पठाउनुहोस्",

  "notFound.title": "यो पृष्ठ भेटिएन",
  "notFound.home": "गृहमा जानुहोस्",
  "crash.title": "BINDU मा समस्या आयो",
  "crash.body": "यो स्क्रिनमा केही बिग्रियो। तपाईंको सुरक्षित डेटा सुरक्षित छ।",
  "crash.retry": "फेरि प्रयास गर्नुहोस्",

  "opt.Beginner": "सुरुवाती",
  "opt.Intermediate": "मध्यम",
  "opt.Advanced": "उन्नत",
  "opt.Culture & heritage": "संस्कृति र सम्पदा",
  "opt.Local food": "स्थानीय खाना",
  "opt.Nature & trekking": "प्रकृति र ट्रेकिङ",
  "opt.Temples & monasteries": "मन्दिर र गुम्बा",
  "opt.Markets & crafts": "बजार र हस्तकला",
  "opt.Off the beaten path": "कम चर्चित ठाउँ",
};

export type Lang = "English" | "नेपाली";
const tables: Record<Lang, Record<I18nKey, string>> = { English: en, नेपाली: ne };

export type Translate = ((key: I18nKey, vars?: Record<string, string | number>) => string) & {
  /** Label for an option value (level, interest, pace, place category...). Unknown values are returned unchanged. */
  opt: (value: string) => string;
};

export function makeTranslator(lang: Lang): Translate {
  const table = tables[lang] ?? en;
  const fill = (s: string, vars?: Record<string, string | number>) => (vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s);
  const t = ((key: I18nKey, vars?: Record<string, string | number>) => fill(table[key] ?? en[key], vars)) as Translate;
  t.opt = (value) => {
    const key = `opt.${value}` as I18nKey;
    return key in table ? table[key] : value;
  };
  return t;
}

/** Translator bound to the language chosen in onboarding/profile. */
export function useT(): Translate {
  const lang = useProfile((s) => s.language);
  return makeTranslator(lang);
}

export const translations = { en, ne };
