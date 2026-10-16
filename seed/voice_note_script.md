# AC Mistri Noida — the simple script (3 people)

| In the group (saved as) | Plays | Character |
|---|---|---|
| **Samyak** | the senior (was "Ramesh") | calm, knows everything |
| **Kaustubh** | the junior (was "Raju") | asks a lot, always says "bhai"; **exports the chat from his phone** |
| **Somil** | the middle one (was "Vikas") | a bit overconfident, also does washing machines |

Samyak and Somil can swap answers in some chats (e.g. chat 5 was answered by Somil). That's fine: just note who **actually** sent each message in the log at the bottom, because the importer credits whoever really sent it.

🎙 = voice note (just say it the way you'd naturally talk, it doesn't have to be word for word) · 📷 = photo · 💬 = text

**The only rules:**
1. One thread takes 5–10 minutes. **Start the next thread at least 35–40 minutes later.** (Set a phone alarm and go do your own work in between.)
2. The facts (what a code means, the safety step) must stay as written. You can say everything else your own way.
3. Kaustubh exports the chat from his phone, so save Samyak and Somil by first name only.

Voltas facts are from the Voltas owner's manual (code table on printed page 30). Daikin facts are from Daikin service manual SiUS091133 (code table on printed page 94). LG AC facts (chats 6, 22) are from the LG Room Air Conditioner service manual MFL41161601 (code tables on printed pp.46–48; p.57: CH05 on the indoor display is the communication error), with LG's lg.com CH05 page for the breaker reset in chat 6. LG washer facts (chats 9, 15, 23) are from LG's washer error-code page on lg.com. The LG room AC service manual (LSN/LSU models) backs the LG drain line in chat 12 (p.6: "Install the drain hose to ensure that water is drained away properly"). The 128-page LG chiller manual is not used. The code tables, with pages, are in `seed/manual_codes.json`; sources are recorded in docs/DECISIONS.md (2026-10-16).

Consent: all three members agreed in writing that their recordings may be used in the demo and video (kept privately, not in this repo).

---

## Day 1

### 1. Voltas E6 ⭐ (record this first; the G2 demo uses it)
📷 **Kaustubh:** *(the AC display showing E6)*
📷 **Kaustubh:** *(the Voltas nameplate)*
💬 **Kaustubh:** Samyak bhai, Voltas 1.5 ton inverter hai, E6 aa raha hai. Outdoor bilkul band pada hai. Kya dekhun?
🎙 **Samyak:** Haan Kaustubh, E6 ka matlab hai indoor aur outdoor aapas mein baat nahi kar rahe, communication fault hai. Outdoor ki board pe light dekhega toh do baar blink karegi. Ab dhyaan se: pehle MCB band kar, aur paanch minute ruk, board pe current reh jaata hai. Phir indoor aur outdoor dono taraf terminal pe jo communication wala taar hai, usko halka sa kheench ke dekh, dheela toh nahi hai ya galat jagah toh nahi laga. Zyaadatar yahi nikalta hai.
💬 **Kaustubh:** *(after 5–10 min)* Bhai sahi pakde 🙏 outdoor pe communication wala taar dheela tha, kas diya. Chal gaya.

### 2. Daikin U4 (Daikin manual p.109–110)
🎙 **Somil:** Samyak bhai, Daikin inverter hai, remote pe U4 aa raha hai, cooling band. Ye bhi Voltas wale E6 jaisa hai kya?
🎙 **Samyak:** Haan, same type ka hai, par Daikin mein iska code U4 hai: indoor aur outdoor ke beech signal nahi pahunch raha. Dhyaan rakhna, Daikin mein E6 ka matlab bilkul alag hai, compressor lock. Har company ka code alag hota hai. Pehle indoor-outdoor ka connection wire dekh, khaas kar 3 number wala; wiring galat toh nahi ya taar toota toh nahi. Kuch bhi kholne se pehle power band karke 10 minute ruk.
💬 **Somil:** Bhai 3 number wala taar beech se toota hua tha, naya daala. Chal gaya.

### 3. Voltas, water dripping
💬 **Kaustubh:** Bhai Voltas split andar se paani phek raha hai, customer pareshaan hai 😅
📷 **Kaustubh:** *(photo of the drain pipe)*
🎙 **Somil:** Arre ye common hai. Humidity zyada ho toh hota hai, par pehle drain pipe ka joint dekh, aksar wahi nikla hota hai. Kaam se pehle power band kar dena.
💬 **Kaustubh:** Haan joint nikla hua tha, tape karke laga diya. Band ho gaya.

### 4. Nobody answers (messy)
💬 **Somil:** Kisi ke paas Samsung window AC ka remote extra pada hai kya?
*(nobody replies, not even an emoji)*

### 5. LG capacitor, with the discharge step
💬 **Kaustubh:** Bhai LG ka outdoor fan ghoom hi nahi raha, compressor bas hmmm kar raha hai
📷 **Kaustubh:** *(photo of a swollen capacitor)*
🎙 **Somil:** Capacitor phool gaya hai, dikh raha hai. Par seedha haath mat lagana. MCB band kar, thoda ruk, phir insulated tool se capacitor discharge kar aur meter laga ke dekh, 5 volt se kam aana chahiye. Tabhi khol. Aur naya wala same rating ka lagana, same µF, same volt.
💬 **Kaustubh:** Discharge karke meter pe 0 aaya, capacitor badla. Fan chal gaya 👍

### 6. LG CH05
🎙 **Somil:** Bhai LG dual inverter pe CH05 aa raha hai
📷 **Somil:** *(the LG nameplate)*
🎙 **Samyak:** CH05 bhi communication wala hai, indoor aur outdoor ki baat nahi ho rahi. LG khud bolta hai ye kabhi kabhi light ke upar-neeche hone se aa jaata hai. Breaker band kar, 5 minute baad wapas on kar. Phir bhi aaye toh service wale ko dikhana padega.
💬 **Somil:** Breaker 5 minute band karke on kiya, CH05 chala gaya. Raat ko voltage gadbad hua tha shayad.

### 7. Voltas remote not working
💬 **Kaustubh:** Customer bol raha remote se AC on hi nahi hota
🎙 **Samyak:** Pehle cell check kar bhai. Phir dekh beech mein kuch aa toh nahi raha. Nahi toh plug nikaal ke dobara laga.
💬 **Kaustubh:** Cell hi khatam the 😂

### 8. Off-topic (messy)
💬 **Somil:** Kal Sector 18 market khula hai? Copper pipe lena tha
💬 **Kaustubh:** Haan khula hai, Sunday band rehta hai

### 9. LG washing machine OE
💬 **Kaustubh:** Somil bhaiya, washing machine ka bhi pooch loon? LG front load mein OE aa raha, paani nikal hi nahi raha
🎙 **Somil:** Pehle plug nikaal. OE matlab drain nahi ho raha. Drain pipe mudi toh nahi, aur neeche wala drain filter khol ke saaf kar.
💬 **Kaustubh:** Filter mein sikka phasa tha 😄 nikaala, chal gayi.

---

## Day 2

### 10. Gas question (safety stop)
🎙 **Kaustubh:** Bhai cooling bilkul nahi, pipe pe oil ka daag hai. Gas refill kitne ka padega? Main khud bhar doon?
🎙 **Samyak:** Nahi nahi, khud mat bharna. Gas ka kaam sirf certified gas technician karega. Pehle leak dhoondh ke theek hona chahiye, phir hi gas. Customer ko bolo jab tak leak theek na ho AC na chalaye.
💬 **Kaustubh:** Theek hai bhai, certified wale ko bulaya, unhone leak theek kiya.

### 11. Voltas P7 (the code isn't on the display)
💬 **Kaustubh:** Bhai Voltas beech beech mein cooling band kar deta hai, display pe koi code nahi
🎙 **Samyak:** Protection wale code display pe nahi aate. Remote pe ADJ button 10 second mein 8 baar daba, code aa jayega.
💬 **Kaustubh:** P7 aaya bhai
🎙 **Samyak:** P7 matlab indoor coil jamne se bachane wala protection. Power band karke filter nikaal ke dho, aur dekh hawa kahin ruk toh nahi rahi.
💬 **Kaustubh:** Filter bahut ganda tha, dhoya, ab theek.

### 12. LG new install dripping
💬 **Kaustubh:** Naya LG lagaya, ek side se tapak raha hai
🎙 **Somil:** Plate tirchi lagi hogi. Plate level honi chahiye aur drain pipe upar ko mudni nahi chahiye.
💬 **Kaustubh:** Haan plate tirchi thi, level kiya.

### 13. Voltas P8
🎙 **Somil:** Bhai Voltas dopahar mein band ho jaata hai, ADJ se dekha toh P8 hai
🎙 **Samyak:** P8 matlab outdoor coil zyada garam ho raha hai. MCB band kar, outdoor ke aas-paas kachra ya saamaan hata, coil saaf kar.
💬 **Somil:** Saamne gatte rakhe the 🤦 hataye, coil saaf ki. Theek hai ab.

### 14. Voltas P3, voltage
🎙 **Somil:** Bhai Voltas raat ko baar baar band, ADJ pe P3
🎙 **Samyak:** P3 voltage ka protection hai, voltage bahut upar-neeche ho raha hai. Ghar ki supply check kar, sahi rating ka MCB ho, aur stabiliser lagwa. Voltas khud stabiliser bolta hai.
💬 **Somil:** Voltage 180 tak gir raha tha, stabiliser lagwa diya.

### 15. LG washing machine IE
📷 **Kaustubh:** *(the washer display showing IE)*
💬 **Kaustubh:** Ye IE kya hai?
🎙 **Somil:** Paani andar nahi aa raha. Tap poora khula hai? Pipe mudi toh nahi? Inlet filter bhi dekh le.
💬 **Kaustubh:** Tap aadha band tha 🙈

### 16. Voltas F9, the argument
💬 **Kaustubh:** Voltas F9, outdoor fan nahi ghoom raha
🎙 **Somil:** Bhai PCB gayi hai, seedha board badal de.
🎙 **Samyak:** Ruk Somil, itni jaldi board mat badlo. F9 matlab outdoor DC fan ka fault hai. MCB band kar, paanch minute ruk, phir dekh fan haath se aaram se ghoomta hai ya kuch phasa hai, aur connector theek laga hai. Board baad mein.
💬 **Kaustubh:** Fan mein patta phasa tha aur connector bhi dheela tha. PCB nahi badli, chal gaya 😎

### 17. Voltas weak cooling
💬 **Kaustubh:** Bhai cooling halki hai, gas toh nahi gayi?
🎙 **Samyak:** Har baar gas nahi hoti. Pehle temperature setting dekh, filter, fan speed, aur khidki-darwaze band hain ya nahi.
💬 **Kaustubh:** Filter ganda tha aur fan low pe tha. Ab sahi thanda.

### 18. The unsure answer (messy)
💬 **Kaustubh:** Outdoor fan ruk ruk ke chalta hai, kya hoga?
🎙 **Somil:** *(sound unsure, about 10 sec)* Hmm… shayad capacitor hoga… ya motor… pata nahi yaar, dekh le…
💬 **Kaustubh:** Capacitor badal ke dekha… abhi toh chal raha hai shayad

---

## Day 3

### 19. Voltas E4
💬 **Kaustubh:** Bhai Voltas E4 aa raha
🎙 **Samyak:** E4 matlab indoor ka room sensor kharab ya connection dheela. MCB band kar, paanch minute ruk, indoor board pe room sensor ka connector dekh.
💬 **Kaustubh:** Room sensor ka connector dheela tha, laga diya. ← **remember this exact line**

### 20. Daikin A5 (Daikin manual p.97–98)
💬 **Kaustubh:** Daikin A5 aa raha, cooling mein band ho jaata hai, coil pe barf
🎙 **Samyak:** A5 freeze-up protection hai: andar ka coil zero degree se neeche chala gaya toh AC khud band karta hai. Teen cheez dekh: hawa ka raasta ruka toh nahi, air filter jam toh nahi, aur indoor coil pe dhool toh nahi jami. Filter nikaalne se pehle power band kar.
💬 **Kaustubh:** Filter poora jam tha, dhoya. Ab theek chal raha.

### 21. Voltas completely dead
💬 **Kaustubh:** AC bilkul dead hai bhai, display bhi nahi
🎙 **Samyak:** Pehle basic: power hai? Plug dheela toh nahi? MCB trip toh nahi? Timer toh nahi laga?
💬 **Kaustubh:** MCB trip tha 😅

### 22. LG CH61
💬 **Somil:** LG CH61, outdoor deewar se chipka hua hai
🎙 **Samyak:** CH61 matlab outdoor zyada garam hua. Usko saans lene ki jagah chahiye. Aas-paas jagah bana, rukawat hata.
💬 **Somil:** Jagah banayi, ab theek.

### 23. LG washing machine UE
💬 **Kaustubh:** Spin pe UE aata hai baar baar
🎙 **Somil:** Kapde ek taraf jama ho gaye. Ek kambal akela ho toh 2–3 kapde aur daal ya kapde faila de.
💬 **Kaustubh:** Haan ek hi kambal tha, towel daale, chal gayi.

### 24. Daikin L5 (Daikin manual p.140–141)
💬 **Kaustubh:** Daikin L5 aa raha, compressor chalte hi band. Kal hi iska ek part badla tha
🎙 **Samyak:** L5 matlab output overcurrent. Ek baar power band karke on kar, dekh phir aata hai kya. Kal part badla tha na? Manual khud bolta hai galat internal wiring se L5 aata hai, toh jo taar nikaale the woh wapas sahi jagah lage hain ya nahi, dekh. Power band karke 10 minute ruk, phir hi kholna. Board ya compressor baad ki baat hai.
💬 **Kaustubh:** Haan bhai, part badalte waqt ek connector ulta lag gaya tha. Sahi kiya, L5 gaya.

### 25. Same fix again (messy, duplicate of 19)
💬 **Kaustubh:** Voltas E4 aa raha phir se, doosri site pe
🎙 **Somil:** Wahi jo Samyak bhai ne bataya tha: indoor board pe room sensor ka connector dekh.
💬 **Kaustubh:** Room sensor ka connector dheela tha, laga diya. ← **same as 19**

### 26. Unclear machine (messy)
💬 **Somil:** Bhai machine chalu karte hi 2 minute mein band ho jaati hai, kya karun?
🎙 **Kaustubh:** Plug aur socket dekh pehle, supply theek hai?
💬 **Somil:** Plug dheela tha.

### 27. Voltas smell
💬 **Somil:** AC chalate hi badboo aati hai
🎙 **Samyak:** AC khud badboo nahi deta, kamre ki smell jama hoti hai. Filter dho de, phir bhi aaye toh service karwa.
💬 **Somil:** Filter dhoya, theek hai.

---

## Recording log + answer key

Fill the last two columns as you go. The answer key must match what really happened, not the plan.

| Chat | Expected | Answer by (plan) | Actually answered by | Recorded? |
|---|---|---|---|---|
| 1 | card ⭐ G2 E6 card | Samyak | Samyak (question: Kaustubh) | ✅ Oct 14 22:30 answered as text; Oct 16 12:47 again with Samyak's voice answer PTT-20261016-WA0029 at 14:03 (the one G2 plays) |
| 2 | card | Samyak | Samyak, voice PTT-20261015-WA0000 (question: Kaustubh by voice, not Somil) | ✅ Oct 14 23:57 |
| 3 | card | Somil | Samyak, voice PTT-20261016-WA0024 (Kaustubh replied by voice WA0025) | ✅ Oct 16 11:03 |
| 4 | no card | — |  |  |
| 5 | card | Somil | Somil, voice PTT-20261015-WA0033 (Kaustubh replied by voice WA0035) | ✅ Oct 15 11:12 |
| 6 | card | Samyak |  |  |
| 7 | card | Somil | Samyak, text | ✅ Oct 15 01:39 |
| 8 | no card | — |  |  |
| 9 | card | Somil |  |  |
| 10 | card (gas STOP) | Samyak | Samyak, voice PTT-20261015-WA0054 (question: Kaustubh by voice WA0053) | ✅ Oct 15 20:41; outcome sent Oct 16 11:00 |
| 11 | card | Samyak |  |  |
| 12 | card | Somil |  |  |
| 13 | card | Samyak |  |  |
| 14 | card | Samyak |  |  |
| 15 | card | Somil |  |  |
| 16 | card (disagreement) | Samyak (Somil disagrees) |  |  |
| 17 | card | Samyak |  |  |
| 18 | needs_review | Somil |  |  |
| 19 | card | Samyak |  |  |
| 20 | card | Samyak |  |  |
| 21 | card | Samyak |  |  |
| 22 | card | Samyak |  |  |
| 23 | card | Somil |  |  |
| 24 | card | Samyak |  |  |
| 25 | merge into 19 | Somil |  |  |
| 26 | needs_review | Kaustubh |  |  |
| 27 | card | Samyak |  |  |

Recorded so far (export of Oct 16, 15:11), in this order: chats 1, 2, 7, 5, 10, 3, then chat 1 again with a voice answer. 9 voice notes so far (Samyak 4, Somil 1, Kaustubh 4). The text-answered first take of chat 1 stays in the group; the importer should merge it with the re-recorded one.

**Gaps in the recorded chats:** in chats 2, 5, 10 and the chat 1 retake the answer came 44 min to 4 h after the question, and chat 10's outcome (Oct 16 11:01) is 2 min before chat 3 starts (11:03). A 30-minute gap rule would split those questions from their answers and join chat 10's outcome to chat 3. For the remaining chats, answer within 30 minutes and keep 35–40 minutes before the next thread; how T13 threads the recorded ones is for T13 to decide. Order does not matter; the 35-minute gap between threads does.

**Totals:** 22 cards, chat 25 merges into 19, chats 18 and 26 go to review, chats 4 and 8 give nothing.
