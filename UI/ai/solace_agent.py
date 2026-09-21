# Import required libraries
import gc
import json
import re
from datetime import date
import torch
from transformers import pipeline as hf_pipeline
from UI.database.database import get_check_in_count,get_check_in_for_date,get_month_check_ins,get_recent_scores
from UI.ui.translations import translate_text, get_text
from UI.ui.resources import resources_for_score

# assistant model and supported languages together
AGENT_MODEL_ID = "Qwen/Qwen3-1.7B"
SUPPORTED_LANGUAGES = {"English","Malay","Chinese","Tamil"}

# tool choices to the functions provided by Solace
TOOL_NAMES = {"solace_help","latest_check_in","recent_scores","wellbeing_context","recent_history","date_check_in","check_in_count","wellbeing_resources","safety_support","general"}

# app information used to answer help questions
SOLACE_HELP = """
Solace is an experimental multimodal wellbeing support application designed
for healthcare workers. It is not a medical diagnostic service.

Check-ins:
- A user can complete an audio or video check-in.
- Whisper creates the speech transcript.
- RoBERTa analyses emotion in the English working transcript.
- MERaLiON analyses emotion in the voice.
- ViT analyses facial-expression emotion when video is used.
- Five supporting signals are available: blink rate, head position, speech rate, disfluency and lexical variety.
- The model scores and supporting signals are fused into a wellbeing score from 0 to 100. A higher score represents a higher estimated wellbeing range.
- Scores of 67 or above are shown as the higher range, 34 to 66 as the moderate range, and below 34 as the lower range.
- Qwen generates supportive recommendations after a check-in.
- NLLB translates recommendations and interface text when Malay, Chinese or Tamil is selected.

Pages:
- Home provides access to the main Solace features.
- Check-in is used to record or upload audio/video and run the analysis.
- Trends displays saved wellbeing history and saved supporting signals.
- Assistant explains Solace and can read the logged-in user's saved wellbeing information through restricted read-only tools.
- Settings allows the application language to be changed.

Languages:
- Solace supports English, Malay, Chinese and Tamil.
- The selected language is used across the interface and for future check-ins.

Privacy and safety:
- Account details and saved check-ins are stored locally on the device.
- The Assistant is read-only and cannot change or delete wellbeing data.
- Solace does not diagnose burnout, depression, anxiety or other conditions.
- AI outputs can be inaccurate and should not replace advice from a qualified healthcare professional.
""".strip()


# Tell model how to choose one read only tool
ROUTER_SYSTEM = """
You are the tool-selection component of the Solace Assistant.
Your only job is to choose the single best read-only tool for the user's question.

Available tools:

solace_help
Use for questions about what Solace is, how it works, pages, models, signals, scores, privacy, languages, settings, check-ins or limitations.

latest_check_in
Use when the user asks specifically about their latest or most recent saved check-in and does not need a broader comparison.

recent_scores
Use when the user asks for recent scores, the previous score, whether scores increased or decreased, or a simple numerical comparison.

wellbeing_context
Use when the user asks why a score changed, what may have contributed to a recent result, or asks for a broader explanation requiring both the latest check-in details and recent scores.

recent_history
Use when the user asks for several recent dated check-ins or a recent history overview.

date_check_in
Use when the user asks about a check-in on a specific date. Return the date as YYYY-MM-DD.

check_in_count
Use when the user asks how many check-ins they have completed.

wellbeing_resources
Use when the user asks for resources, help, tips, activities, exercises, support, or something they can do to feel better, cope, relax or improve their wellbeing.

safety_support
Use when the user describes possible immediate danger, self-harm,
suicidal intent, or an urgent medical or mental-health crisis.

general
Use only for greetings, thanks, or general conversation that does not require Solace documentation or saved user data.

Rules:
- Choose exactly one tool.
- Never invent another tool.
- Personal wellbeing questions must use a personal-data tool.
- Medical diagnosis questions should use solace_help unless there is immediate danger, in which case use safety_support.
- If a specific date is mentioned, resolve it using the current date when possible and use date_check_in.
- Return JSON only with exactly these keys: {"tool": "tool_name", "date": "YYYY-MM-DD or empty string"}

/no_think
""".strip()

# rules for answering from saved data and tool results
ANSWER_SYSTEM = """
You are the Solace wellbeing support assistant.
Use only the supplied Solace tool result when stating facts about the logged-in user's saved wellbeing data.
Never invent a score, signal, check-in, date, transcript or trend.
You may explain Solace using the supplied application information.

Safety boundaries:
- Do not diagnose burnout, depression, anxiety or any medical or mental-health condition.
- Do not claim that a Solace score proves a condition.
- Do not provide medication or treatment instructions.
- Explain that Solace is an experimental wellbeing support tool when medical certainty is requested.
- If information is unavailable, say that it is unavailable.
- Do not claim that you changed, deleted or sent any user data.
- Keep the response supportive, concise and clear.
- When the tool result contains resources, introduce them warmly in one sentence, then list each resource's title and its description. Include each resource's exact url from the tool result on its own. Never invent, change or add any url. Only use urls present in the tool result.
- Answer in English. Another model will translate the final response when the user has selected another language.

/no_think
""".strip()

# Answer questions using Solace information and user saved history
class SolaceAgent:
    # Qwen is loaded once and shared by every reply so it is not reloaded each time
    _shared_qwen = None
    def __init__(self,user_id=None,language_name="English"):
        # user and fall back to English for unsupported languages
        self.user_id = user_id
        self.language_name = (language_name if language_name in SUPPORTED_LANGUAGES else "English")
        # Load Qwen only when reply needs it
        self.qwen = None
        self.last_tool = None

    # switch account used for personal data queries
    def set_user(self, user_id):
        self.user_id = user_id

    # Accept only supported interface languages
    def set_language(self, language_name):
        if language_name in SUPPORTED_LANGUAGES:
            self.language_name = language_name

    # load Qwen once and reuse it for current reply
    def load_qwen(self):
        # shared model so it loads from disk only on the first question
        if SolaceAgent._shared_qwen is None:
            SolaceAgent._shared_qwen = hf_pipeline("text-generation", model=AGENT_MODEL_ID, device_map="auto", dtype="auto")
        self.qwen = SolaceAgent._shared_qwen
        return self.qwen

    # release Qwen and clear unused memory
    def release_qwen(self):
        # shared model loaded for the next question
        self.qwen = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def clean_history(history):
        if not history:
            return []
        cleaned = []
        # Use only eight most recent messages
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = str(item.get("content", "")).strip()

            # Skip empty messages and roles the assistant does not accept
            if (role not in {"user","assistant"} or not content):
                continue

            # Limit each message to 1000 characters
            cleaned.append({"role": role,"content": content[:1000]})

        return cleaned

    # reply text from either model output format
    @staticmethod
    def generated_content(result):
        # generated
        generated = result[0]["generated_text"]

        if isinstance(generated, list):
            text = str(generated[-1].get("content","",))
        else:
            text = str(generated)

        # Remove complete or unfinished thinking sections
        text = re.sub(r"<think>.*?</think>","",text,flags=re.DOTALL)
        text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
        text = text.replace("<think>", "").replace("</think>", "")

        # return text
        return text.strip()


    # Read and check the model tool selection JSON
    @staticmethod
    def parse_decision(text):
        # JSON object and fall back to app help if it is missing
        match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not match:
            return {"tool": "solace_help","date": ""}

        try:
            # decision
            decision = json.loads(match.group(0))

        # app help when the JSON cannot be read
        except json.JSONDecodeError:
            return {"tool": "solace_help","date": "" }
        tool = decision.get("tool","")
        date_text = str(decision.get("date","")).strip()
        # unknown tools with the app help tool
        if tool not in TOOL_NAMES:
            tool = "solace_help"
        # clear do not match the required year month day format
        if (tool == "date_check_in" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text)):
            date_text = ""
        return {"tool": tool, "date": date_text}

    @staticmethod
    def fast_tool(question):
        # Normalise the question before matching keywords
        text = question.lower()
        # use resource tool
        if any(word in text for word in ("resource", "tips", "exercise", "activit", "relax", "cope", "coping", "help me feel")):
            return "wellbeing_resources"
        # Direct count questions
        if any(word in text for word in ("how many check", "how many checkin")):
            return "check_in_count"
        return None

    # choose a tool for the question
    def choose_tool(self,question,history=None):
        generator = self.load_qwen()
        conversation = self.clean_history(history)
        # four recent messages for context
        context = "\n".join((f"{item['role']}: {item['content']}") for item in conversation[-4:])
        # router today date selected language and current question
        messages = [
            {
                "role": "system",
                "content": ROUTER_SYSTEM,
            },
            {
                # role user and consent
                "role": "user",
                "content": (
                    f"Current date: "
                    f"{date.today().isoformat()}\n"
                    f"Selected application language: "
                    f"{self.language_name}\n\n"
                    f"Recent conversation:\n"
                    f"{context or 'None'}\n\n"
                    f"Current user question:\n"
                    f"{question}\n\n"
                    "Return the tool-selection "
                    "JSON only."
                ),
            },
        ]
        # short decision without random sampling
        result = generator(messages,max_new_tokens=60,do_sample=False,pad_token_id=(generator.tokenizer.eos_token_id),)
        return self.parse_decision(self.generated_content(result))

    # user most recent saved check-in
    def latest_check_in(self):
        history = get_month_check_ins(self.user_id,31,)
        # clear status when there is no saved history
        if not history:
            return {
                "status": "no_data",
                "message": ("No saved check-ins are available.")
            }

        # latest saved date to retrieve the full check in
        latest_date = history[-1]["date"]
        check_in = get_check_in_for_date(self.user_id,latest_date,)

        # history entry whose details cannot be retrieved
        if check_in is None:
            return {"status": "no_data", "message": ("No saved check-in could be retrieved.")}

        return {"status": "ok","date": latest_date,"check_in": check_in}


    # latest seven wellbeing scores
    def recent_scores(self):
        scores = get_recent_scores(self.user_id,7,)
        # Report user has no saved scores
        if not scores:
            return {
                "status": "no_data",
                "message": ("No saved wellbeing scores are available.")
            }

        # Return scores in time order with the latest and previous values
        return {
            "status": "ok",
            "scores_chronological": [round(score,2,) for score in scores],
            "latest_score": round(scores[-1], 2),
            "previous_score": (round(scores[-2], 2) if len(scores) >= 2 else None)
        }

    # Combine latest check in with recent scores for context
    def wellbeing_context(self):
        latest = self.latest_check_in()
        scores = self.recent_scores()
        return {"latest_check_in": latest,"recent_scores": scores}


    # Read up ten recent dated check-ins
    def recent_history(self):
        history = get_month_check_ins(self.user_id,10,)
        if not history:
            return {"status": "no_data","message": ("No saved check-in history is available.")}
        return {"status": "ok","check_ins": history,}

    # Retrieve check in saved on a requested date
    def date_check_in(self,date_text):
        # Ask for date when none was identified
        if not date_text:
            return {"status": "missing_date","message": ("A specific check-in date was not identified.")}

        # check in
        check_in = get_check_in_for_date(self.user_id,date_text)

        # Report when no check in exists for that date
        if check_in is None:
            return {
                "status": "no_data",
                "date": date_text,
                "message": ("No saved check-in is available for this date.")
            }
        return {"status": "ok","date": date_text,"check_in": check_in}

    # Count user saved check-ins
    def check_in_count(self):
        return {"status": "ok","count": get_check_in_count(self.user_id)}

    # wellbeing resources using the latest score when available
    def wellbeing_resources(self):
        # scores
        scores = get_recent_scores(self.user_id, 7) if self.user_id else []
        # latest
        latest = scores[-1] if scores else None
        # picked
        picked = resources_for_score(latest, self.language_name)
        # resource list
        resources = []
        # Translate resource names and descriptions while keeping their links
        for item in picked["resources"]:
            resources.append({
                "title": get_text(self.language_name, item["title_key"]),
                "description": get_text(self.language_name, item["desc_key"]),
                "url": item["url"]
            })
        # return ok
        return {
            "status": "ok",
            "latest_score": round(latest, 2) if latest is not None else None,
            "band": picked["band"],
            "resources": resources
        }


    # resource reply directly so the answer model is not needed
    def format_resources(self, tool_result):
        resources = tool_result.get("resources", [])
        # Fall back gently when no resource is available
        if not resources:
            return "I don't have any resources to suggest right now."
        # opening line followed by each resource and its exact url
        lines = ["Here are a few resources that might help:"]
        for item in resources:
            lines.append(f"\n**{item['title']}** — {item['description']}\n{item['url']}")
        return "\n".join(lines)

    # fixed message for urgent support
    @staticmethod
    def safety_support():
        # return urgent safety
        return {
            "status": "safety",
            "message": (
                "Solace cannot provide emergency "
                "or crisis care. "

                "If you may be in immediate danger "
                "or may harm yourself or someone "
                "else, contact local emergency "
                "services or a trusted person who "
                "can stay with you. "

                "For urgent mental-health concerns, "
                "seek help from a qualified "
                "healthcare professional."
            )
        }


    # selected read only tool
    def run_tool(self,decision):
        tool = decision["tool"]
        # urgent support and general chat without personal data
        if tool == "solace_help":
            return {"status": "ok","information": SOLACE_HELP}
        # safety support
        if tool == "safety_support":
            return self.safety_support()
        # general
        if tool == "general":
            # status ok
            return {
                "status": "ok",
                "message": (
                    "This is a general or conversational message that "
                    "does not need Solace documentation or saved user "
                    "data. Reply warmly in one or two sentences, then "
                    "gently remind the user you can explain how Solace "
                    "works or help them understand their saved wellbeing "
                    "history. Do not say you cannot answer."
                )
            }

        # logged in user before accessing personal wellbeing tools
        if self.user_id is None:
            # status ok
            return {
                "status": "no_user",
                "message": ("Personal wellbeing information is only available for a logged-in user.")
            }

        # choice to its matching data or resource function
        if tool == "latest_check_in":
            return self.latest_check_in()

        if tool == "recent_scores":
            return self.recent_scores()

        if tool == "wellbeing_context":
            return self.wellbeing_context()

        if tool == "recent_history":
            return self.recent_history()

        if tool == "date_check_in":
            return self.date_check_in(decision["date"])

        if tool == "check_in_count":
            return self.check_in_count()

        if tool == "wellbeing_resources":
            return self.wellbeing_resources()
        return {
            "status": "unsupported",
            "message": ("The requested Solace tool is not available.")
        }


    # selected tool result
    def generate_answer(self,question,tool_name,tool_result,history=None,):
        generator = self.load_qwen()
        conversation = self.clean_history(history)
        # Convert tool result to JSON without escaping non English text
        tool_text = json.dumps(tool_result,ensure_ascii=False,)
        # Combine answer rules recent chat and current tool result
        messages = [{"role": "system","content": ANSWER_SYSTEM,},]
        messages.extend(conversation)
        # append the messages
        messages.append(
            {
                "role": "user",
                "content": (
                    f"User question:\n"
                    f"{question}\n\n"
                    f"Tool selected: "
                    f"{tool_name}\n\n"
                    f"Tool result:\n"
                    f"{tool_text}\n\n"
                    "Answer the user's question using the tool result and the safety rules."
                )
            }
        )

        # concise reply without random sampling
        result = generator(messages,max_new_tokens=128,do_sample=False,pad_token_id=(generator.tokenizer.eos_token_id))
        answer = self.generated_content(result)
        # helpful fallback if the generated reply is empty
        if not answer:
            answer = ("I can help you understand how Solace works or explore your saved wellbeing history. Could you tell me a little more about what you would like to know?")
        return answer

    # common greetings without loading Qwen
    @staticmethod
    def quick_reply(question):
        # common phrases
        text = question.strip().lower().rstrip("!.?")
        greetings = {"hi", "hii", "hello", "hey", "yo","good morning", "good afternoon", "good evening"}
        thanks = {"thanks", "thank you", "thx", "ty", "thankyou"}
        how_are_you = {"how are you", "how are you today", "how r u","how are u", "hows it going", "how's it going","how do you do", "you okay", "are you okay"}
        who_are_you = {"who are you", "what are you", "what is this","what can you do", "what do you do"}
        # Common "how it works" questions answered from the fixed app description
        how_it_works = {"how does solace work", "how does this work", "how do you work",
                        "what is solace", "what does solace do", "how does the app work",
                        "how solace works", "explain solace", "how does it work"}

        # ready made reply for recognised conversation starters
        if text in greetings:
            return ("Hi! I can explain how Solace works or help you understand your saved wellbeing history. What would you like to know?")
        if text in thanks:
            return "You are welcome. Is there anything else about Solace I can help with?"
        if text in how_are_you:
            return ("I am doing well, thank you! I am here to help you with Solace. I can explain how it works or walk you through your saved wellbeing history. What would you like to know?")
        if text in who_are_you:
            return ("I am the Solace Assistant. I can explain how Solace works and help you understand your own saved wellbeing check-ins. I only read your locally saved Solace information.")
        # Ready made explanation so this common question needs no model
        if text in how_it_works or ("solace" in text and "work" in text):
            return (
                "Solace is an experimental wellbeing support tool for healthcare workers. "
                "In a check-in you record or upload a short audio or video clip. Whisper writes "
                "the transcript, and AI models read the emotion in your words, your voice and "
                "(for video) your facial expression, along with supporting signals like blink rate, "
                "head position, speech rate, disfluency and lexical variety. These are combined into "
                "a wellbeing score from 0 to 100 a higher score means a higher estimated wellbeing "
                "range and Solace then offers supportive recommendations. Everything is stored "
                "locally on your device, and Solace does not diagnose any condition."
            )
        return None

    # return the answer in the selected language
    def answer(self,question,history=None,):
        question = str(question).strip()
        # Prompt user when the question is empty
        if not question:
            return {
                "answer": ("Please enter a question for the Solace Assistant."),
                "tool": "none"
            }
        # quick reply for simple greetings
        quick = self.quick_reply(question)
        if quick is not None:
            self.last_tool = "general"
            return {"answer": translate_text(quick, self.language_name),"tool": "general"}
        try:
            # Choose tool and read the information needed for the answer
            tool = self.fast_tool(question)
            if tool is None:
                decision = self.choose_tool(question, history)
            else:
                decision = {"tool": tool, "date": ""}
            self.last_tool = decision["tool"]
            tool_result = self.run_tool(decision)
            # fixed urgent support message
            if (decision["tool"] == "safety_support"):
                english_answer = (tool_result["message"])
            # resources are already final
            elif (decision["tool"] == "wellbeing_resources" and tool_result.get("status") == "ok"):
                english_answer = self.format_resources(tool_result)
            else:
                # english answer
                english_answer = (self.generate_answer(question,decision["tool"],tool_result,history))

            # Release Qwen before translating reply
            self.release_qwen()
            final_answer = translate_text(english_answer,self.language_name,)
            return {
                "answer": final_answer,
                "tool": decision["tool"]
            }

        # release Qwen even when generating reply fails
        except Exception:
            self.release_qwen()
            raise