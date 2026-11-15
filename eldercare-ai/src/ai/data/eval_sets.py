"""Held-out evaluation utterances. NEVER used for training. Hand-written, small, English only.

Because the sets are small and written by the project author, accuracy figures are
indicative, not a guarantee of real-world performance.
"""

INTENT_EVAL = [
    ("medicines_today", "which medicines are for today"), ("medicines_today", "can you list my tablets"),
    ("medicines_today", "what pills should be taken today"), ("medicines_today", "show me today's medication"),
    ("next_medicine", "what is the next tablet i have"), ("next_medicine", "when do i take my next medicine"),
    ("next_medicine", "next pill please"),
    ("caregiver", "what is my son's number"), ("caregiver", "who is looking after me"),
    ("caregiver", "how can i contact my caregiver"), ("caregiver", "give me my family's phone number"),
    ("appointment", "do i have a doctor visit coming"), ("appointment", "when is my next clinic appointment"),
    ("appointment", "any appointments this week"), ("appointment", "tell me my hospital appointment"),
    ("checkin", "did i do my wellness check-in today"), ("checkin", "what is the daily check in"),
    ("checkin", "have i completed my check in"),
    ("time_date", "what is the time"), ("time_date", "tell me today's date"), ("time_date", "what day is today"),
    ("greeting", "hello there"), ("greeting", "good morning"), ("greeting", "hi"),
    ("how_are_you", "how are you feeling today"), ("how_are_you", "how are you doing today"),
    ("thanks", "thank you very much"), ("thanks", "thanks for helping"), ("thanks", "thank you"),
    ("feeling", "i am feeling very lonely today"), ("feeling", "i feel sad"), ("feeling", "i am worried"),
    ("feeling", "i feel down and tired"),
    ("medical_advice", "what dosage should i use"), ("medical_advice", "should i stop taking my tablets"),
    ("medical_advice", "do i have a heart problem"), ("medical_advice", "can you prescribe me something"),
    ("medical_advice", "which tablet is good for fever"),
    ("knowledge_question", "how do i prevent a fall in the house"), ("knowledge_question", "tips for sleeping well"),
    ("knowledge_question", "how can i stay safe from phone scams"), ("knowledge_question", "what exercise is good for me"),
    ("set_reminder", "remind me to drink tea at 4 pm"), ("set_reminder", "set a reminder for my walk at 5 pm"),
    ("set_reminder", "please remind me to call my daughter at 8 pm"),
    ("open_chat", "tell me a joke please"), ("open_chat", "what is the weather today"),
    ("open_chat", "can you tell me a story"), ("open_chat", "suggest something to cook"),
    ("open_chat", "tell me an interesting fact"), ("open_chat", "let us have a chat"),
]

URGENCY_EVAL = [
    ("emergency", "i have terrible chest pain"), ("emergency", "i can not breathe"),
    ("emergency", "i have fallen and i cannot stand up"), ("emergency", "please call an ambulance now"),
    ("emergency", "i think i am having a heart attack"), ("emergency", "i am bleeding a lot"),
    ("emergency", "i am going to faint"), ("emergency", "i have taken too many pills"),
    ("emergency", "my speech is slurred and my face is drooping"), ("emergency", "i passed out in the kitchen"),
    ("urgent", "i feel dizzy since morning"), ("urgent", "i have a fever"),
    ("urgent", "i missed my medicines for two days"), ("urgent", "my legs are swollen today"),
    ("urgent", "i feel very weak and tired"), ("urgent", "i have a bad headache"),
    ("urgent", "i am not feeling well at all"), ("urgent", "my vision is blurry"),
    ("routine", "what medicines do i take today"), ("routine", "tell me a joke"),
    ("routine", "when is my next appointment"), ("routine", "good morning"),
    ("routine", "i had a nice walk today"), ("routine", "who is my caregiver"),
    ("routine", "thank you"), ("routine", "what is the date today"),
]


# Harder intent cases: typos, indirect or voice-transcript-like phrasing.
INTENT_EVAL_HARD = [
    ("medicines_today", "whats my tablets for today"), ("medicines_today", "medicin list pls"),
    ("next_medicine", "wen is next pill"), ("caregiver", "i need to talk to my son what is his number"),
    ("appointment", "is the doctor expecting me soon"), ("checkin", "i forgot my daily check did i do it"),
    ("time_date", "whats the time now"), ("greeting", "hello good day"),
    ("feeling", "i am feeling very alone these days"), ("medical_advice", "is it ok to take double dose"),
    ("knowledge_question", "how to keep cool when its very hot"), ("set_reminder", "remind me about my walk 6 pm"),
    ("open_chat", "can you tell me about the monsoon"), ("open_chat", "i am bored entertain me"),
]

# FRESH urgency cases: written after the first evaluation run and not used to tune training data.
URGENCY_EVAL_FRESH = [
    ("emergency", "i lost consciousness for a moment"), ("emergency", "my chest is very painful and my arm is numb"),
    ("emergency", "i accidentally swallowed lots of pills"), ("emergency", "i slipped and hit my head and feel sick"),
    ("emergency", "i can hardly breathe"), ("emergency", "there is smoke in the house and i cannot get out"),
    ("emergency", "my wife is not responding"), ("emergency", "i am vomiting blood"),
    ("urgent", "i have a high temperature"), ("urgent", "i feel giddy when i stand up"),
    ("urgent", "i have not taken my tablets for three days"), ("urgent", "my ankle is swollen and painful"),
    ("urgent", "i am coughing a lot at night"), ("urgent", "i feel extremely tired and weak"),
    ("routine", "show my medicines"), ("routine", "what is the time"), ("routine", "tell me a story"),
    ("routine", "hello how are you"), ("routine", "i enjoyed my lunch"), ("routine", "when is the doctor visit"),
    ("routine", "i am bored"), ("routine", "thank you for the reminder"),
]


# Knowledge-base retrieval: (question, expected document id). OUT_OF_KB questions should retrieve nothing.
RAG_EVAL = [
    ("how can i stop falling at home", "fall-prevention-at-home"), ("what lighting helps prevent trips", "fall-prevention-at-home"),
    ("how do i remember my pills", "medicine-safety-habits"), ("is it okay to skip a medicine when i feel better", "medicine-safety-habits"),
    ("how much should i drink in summer", "staying-hydrated"), ("why do older people feel less thirsty", "staying-hydrated"),
    ("how can i sleep better", "sleep-routine"), ("is napping in the day bad", "sleep-routine"),
    ("what exercises are good for older people", "staying-active"), ("how do i start moving more", "staying-active"),
    ("i feel lonely what can i do", "loneliness-and-social-contact"), ("ways to meet people", "loneliness-and-social-contact"),
    ("how to stay safe in the heat", "hot-weather-safety"), ("signs of heat illness", "hot-weather-safety"),
    ("someone asked for my otp", "scam-calls-and-online-safety"), ("is this call from my bank real", "scam-calls-and-online-safety"),
    ("what should i eat", "healthy-eating-basics"), ("food for diabetes", "healthy-eating-basics"),
    ("how can i keep my memory good", "keeping-your-mind-active"), ("brain games", "keeping-your-mind-active"),
]
OUT_OF_KB = ["what is the capital of france", "tell me a joke", "who won the cricket match", "how do i fix my car",
             "what is the price of gold", "translate hello into tamil"]

# Reminder understanding: (utterance, expected task, expected time, expected problem)
REMINDER_EVAL = [
    ("remind me to drink water at 5 pm", "Drink water", "17:00", None),
    ("set a reminder for my walk at 6 pm", "My walk", "18:00", None),
    ("please remind me to call my son at 7:30 in the evening", "Call my son", "19:30", None),
    ("remind me to water the plants in the morning at 8", "Water the plants", "08:00", None),
    ("remind me about yoga at 6 am", "Yoga", "06:00", None),
    ("remind me to rest at noon", "Rest", "12:00", None),
    ("remind me to call home at 17:30", "Call home", "17:30", None),
    ("remind me to take a walk at 4", "Take a walk", None, "ambiguous_time"),
    ("remind me to read", "Read", None, "no_time"),
    ("remind me to take my tablets at 8 pm", "Take my tablets", "20:00", "medicine"),
]


# Prescription text samples: (text, expected [(name, strength)]). Includes noisy lines and a known-hard one.
DOC_EVAL = [
    ("""Dr. A. Kumar, City Clinic
Patient: Test Person   Age: 70   Date: 12/11/2026
Rx
1. Tab. Metformin 500 mg  1-0-1 after food
2. Tab. Amlodipine 5 mg  once daily morning
3. Cap. Omeprazole 20 mg  before breakfast for 10 days
4. Tab. Atorvastatin 10 mg  at night
Follow up after 2 weeks""", [("Metformin", "500 mg"), ("Amlodipine", "5 mg"), ("Omeprazole", "20 mg"), ("Atorvastatin", "10 mg")]),
    ("""City Hospital OPD
Name: Sample Patient
Tab Telmisartan40mg OD morning
Tab. Dolo 650 mg SOS
Syp. Cheston 5 ml TDS after food x 5 days
Cap. Vit D3 60000 IU once weekly""", [("Telmisartan", "40mg"), ("Dolo", "650 mg"), ("Cheston", "5 ml"), ("Vit D3", "60000 IU")]),
    ("""Patient name: Sample Person
Age: 68  Weight: 60 kg  BP: 130/80
Diagnosis: routine review
Advice: walk daily, drink water
Next visit: after one month""", []),
]
