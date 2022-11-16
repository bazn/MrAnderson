# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"
import logging
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import UserUtteranceReverted, ConversationPaused, EventType, AllSlotsReset, SlotSet


from actions.m42 import M42API

logger = logging.getLogger(__name__)
vers = "vers: 1.0.0, date: Nov 1, 2022"
logger.debug(vers)

m42 = M42API()

class ActionOpenIncident(Action):
    def name(self) -> Text:
        return "action_open_incident"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Create an incident and return TicketNumber.
        """
        try:
            user_information_str = tracker.sender_id
            user_information_str_dict = eval(user_information_str)             
            email = user_information_str_dict.get("email")                 
        except:
            dispatcher.utter_message(f"Sorry - du scheinst nicht in Teams angemeldet zu sein. Bitte melde dich an und versuche es erneut.")
            logger.debug("Error: No Teams user information found")
            return [AllSlotsReset()]
        
        ticket_description = tracker.get_slot("ticket_description")
        ticket_title = tracker.get_slot("ticket_title")
        confirm = tracker.get_slot("confirm")
        if not confirm:
            dispatcher.utter_message(
                response="utter_incident_creation_canceled"
            )
            return [AllSlotsReset()]

        
        response = m42.create_ticket(
            description=ticket_description,
            short_description=ticket_title,
            email=email,
        )
        ticket_number = response
        
        if ticket_number:
            message = (
                f"Ticket mit der Nummer {ticket_number} "
                f"wurde erfolgriech erstellt. Es wird sich so schnell wie möglich jemand um dein Anliegen kümmern."
            )
        else:
            message = (
                f"Bei erstellen des Tickets ist ein Fehler aufgetreten. "
                f"{response.get('error')}"
            )
        dispatcher.utter_message(message)
        return [AllSlotsReset()]


class ActionDefaultFallback(Action):
    def name(self) -> Text:
            return "action_default_fallback"
    def run(self, dispatcher, tracker, domain):
            # output a message saying that the conversation will now be
            # continued by a human.
    
            message = "Sorry! Let me connect you to a human..."
            dispatcher.utter_message(text=message)
    # pause tracker
            # undo last user interaction
            return [ConversationPaused(), UserUtteranceReverted()]


class ActionQueryFAQ(Action):
    def name(self) -> Text:
            return "action_query_faq"
    def run(self, dispatcher, tracker, domain):
            faqs = m42.search_faq(tracker.latest_message["text"])
            Kbarticles = faqs["KbArticles"]

            if len(Kbarticles) > 0:
                dispatcher.utter_message("Ich habe folgende FAQ gefunden:")
                
                for article in Kbarticles:
                    ticketNr = article["TicketNumber"] 
                    title = article["Subject"]
                    link = "https://srvwsm001.imagoverum.com/M42Services/HelpDesk/Article/" + str(ticketNr)
                    dispatcher.utter_message(f"[{ticketNr} - {title}]({link})")
            else:
                dispatcher.utter_message("Ich habe leider keine passende FAQ gefunden.")        
            return []


