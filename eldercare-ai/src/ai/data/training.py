"""Hand-written training utterances for the two local classifiers.

Small by design: this is a demonstration dataset, written for this project, English only.
The held-out evaluation sets live in eval_sets.py and are never used for training.
"""

INTENTS = {
    "medicines_today": [
        "what medicines do i take today", "which tablets should i take today", "show my medicines for today",
        "what pills do i have today", "tell me my medication schedule", "list my medicines",
        "what medicine is due today", "which medicines have i taken today", "did i take my tablets",
        "what is on my medicine list", "my medication for today please", "read out my medicines",
        "what tablets are scheduled", "medicine schedule", "do i have any medicines left today"],
    "next_medicine": [
        "when is my next medicine", "what is my next tablet", "which medicine is next",
        "when should i take my next pill", "what is the next medication on my list", "next medicine time",
        "what do i take next", "when is my next medicine reminder", "which tablet comes next",
        "what is my upcoming medicine", "when is the next pill due"],
    "caregiver": [
        "who is my caregiver", "give me my son's phone number", "how do i contact my family",
        "what is my caregiver's number", "who can i call", "my caregiver phone number please",
        "i want to call my son", "contact details of my caregiver", "who looks after me",
        "how can i reach my son", "family contact", "which number should i call for my family"],
    "appointment": [
        "when is my next appointment", "do i have any appointments", "when do i see the doctor",
        "what appointments are coming up", "tell me about my clinic visit", "my doctor appointment",
        "is there a check-up this week", "any hospital visit planned", "what is my next doctor visit",
        "appointment details please", "when is my clinic appointment", "when do i go to the clinic"],
    "checkin": [
        "have i done my check in today", "did i complete today's check-in", "what is my daily check in",
        "do i need to do a check-in", "how do i do the wellness check", "have i recorded my mood today",
        "did i do my daily check", "check-in status", "wellness check in today", "have i filled my daily check-in"],
    "time_date": [
        "what time is it", "what is the time now", "what is today's date", "what day is it today",
        "tell me the date", "which day is today", "what is the date today", "can you tell me the time",
        "time please", "what's the day today"],
    "greeting": ["hello", "hi there", "good morning", "good afternoon", "good evening", "hey", "namaste",
                 "hello assistant", "hi", "hey there"],
    "how_are_you": ["how are you", "how are you today", "how are you doing", "are you okay",
                    "how is your day", "how is everything with you"],
    "thanks": ["thank you", "thanks a lot", "thanks", "thank you so much", "that was helpful thanks",
               "many thanks", "thank you for your help", "ok thanks"],
    "feeling": [
        "i feel sad today", "i am feeling lonely", "i am tired", "i am worried about something",
        "i feel anxious", "i had a bad day", "i feel upset", "i am scared", "i feel low and alone",
        "feeling a bit down", "i am so tired today", "i miss my family", "i feel bored and lonely",
        "i am stressed", "i feel restless tonight"],
    "medical_advice": [
        "what dose should i take", "should i take more tablets", "how many tablets should i take",
        "can i stop my medicine", "do i have diabetes", "what are the side effects of my medicine",
        "can you prescribe something for my pain", "should i skip my tablet today",
        "is it safe to double my medicine", "which medicine is best for fever", "what should i take for a headache",
        "can i take two pills together", "what is the right amount of medicine", "diagnose my cough",
        "is this rash dangerous", "what is wrong with me"],
    "knowledge_question": [
        "how can i prevent falls at home", "tips to sleep better at night", "how can i stay hydrated",
        "what are some safe exercises for older people", "how do i stop feeling lonely",
        "how to stay cool in hot weather", "how can i spot a scam call", "what should i eat to stay healthy",
        "how can i remember to take my tablets on time", "how do i make my house safer",
        "ideas to stay active at home", "how to keep my mind active", "how do i stay safe online",
        "tips for a good bedtime routine", "why is it important to drink water", "how can i avoid slipping in the bathroom",
        "what is a healthy diet for older people", "how can i feel less lonely", "how do i keep my memory sharp",
        "safety tips for hot summer days", "how do i store my medicines safely"],
    "set_reminder": [
        "remind me to drink water at 5 pm", "set a reminder for my walk at 6 pm",
        "please remind me to call my son at 7:30 in the evening", "remind me to water the plants in the morning at 8",
        "can you remind me about my yoga at 6 am", "set a reminder to feed the cat at 9 am",
        "i want a reminder to read at 8 pm", "remind me to take a walk at 4 pm", "reminder for prayer at 6 in the morning",
        "set a reminder for tea at 4 pm", "please remind me to phone my sister tomorrow at 10 am",
        "remind me to lock the door at night at 9", "remind me to call my friend at noon", "set an alarm reminder to stretch at 7 am"],
    "open_chat": [
        "tell me a joke", "what is the weather like", "tell me a story", "what should i cook for dinner",
        "tell me about yourself", "can you sing a song", "what is the capital of france",
        "recommend a good book", "talk to me", "i want to chat", "tell me something interesting",
        "how do i make tea", "suggest a hobby", "what can we talk about", "teach me a new word",
        "what are some light indoor activities", "give me a recipe for khichdi", "tell me about kerala",
        "how can i use a smartphone", "what is a good game to play", "tell me a fun fact",
        "who wrote the ramayana"],
}

# Urgency: routine / urgent / emergency. Routine examples are all the intent utterances above
# except medical_advice-style and feeling ones, plus the extras below.
URGENCY = {
    "emergency": [
        "i have chest pain", "i cannot breathe", "i fell and cannot get up", "call an ambulance",
        "i think i am having a heart attack", "i am bleeding badly", "i feel like i will faint",
        "i have severe pain in my chest", "i can't breathe properly", "i am having a stroke",
        "my face is drooping and my speech is slurred", "help i have fallen", "i hit my head and i am bleeding",
        "i am choking", "sudden severe headache and i cannot see", "i took too many tablets",
        "i fainted just now", "there is a fire in my house", "someone broke into my house",
        "i am very dizzy and cannot stand", "severe pain in my stomach and i cannot move",
        "my husband is unconscious", "i collapsed in the bathroom", "i have crushing pain in my chest",
        "i am about to faint", "i passed out", "i blacked out", "i swallowed too many tablets",
        "i took an overdose", "i am unable to breathe", "i feel i am going to collapse"],
    "urgent": [
        "i feel dizzy", "i have had a fever since yesterday", "i missed my medicine twice",
        "my legs are swollen", "i have not slept for two nights", "i feel very weak",
        "i have a bad cough for a week", "i have pain in my knee", "i am not feeling well",
        "i have not eaten since yesterday", "my chest feels a little tight today", "i keep forgetting my tablets",
        "i have a headache that will not go away", "i feel nauseous and vomited", "i feel confused today",
        "i have pain when i pass urine", "my vision is blurry today", "i have a swollen ankle after a slip",
        "i feel breathless when i climb stairs", "i have been very thirsty and tired", "i have not taken my tablets for days",
        "i forgot my medicines yesterday and today", "i feel giddy", "i have a high fever"],
    "routine_extra": [
        "i slept well last night", "i went for a walk this morning", "my garden looks lovely today",
        "i had a good breakfast", "i met my neighbour today", "i watched a nice programme",
        "the day is going well", "i am feeling happy today"],
}
