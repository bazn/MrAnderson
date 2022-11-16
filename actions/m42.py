import logging
import requests
import json
import pathlib
import ruamel.yaml
from typing import Dict, Text, Any

logger = logging.getLogger(__name__)

here = pathlib.Path(__file__).parent.absolute()

json_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

class M42API(object):
    """class to connect to the M42 API"""

    def __init__(self):
        m42_config = (
            ruamel.yaml.safe_load(open(f"{here}/m42_credentials.yml", "r"))
            or {}
        )
        self.M42_apitoken = m42_config.get("token")   
        self.M42_baseurl = m42_config.get("base_url")      
        self.base_api_url = "https://" + format(self.M42_baseurl) + "/M42Services/api"
        self.userToken = ""

    def handle_request(
        self, request_method=requests.get, request_args={}
    ) -> Dict[Text, Any]:
        result = dict()
        try:
            response = request_method(**request_args, verify=False)
            result["status_code"] = response.status_code
            if response.status_code >= 200 < 300:
                result["content"] = response.json()
            else:
                error = (
                    f"M42 error: {response.status_code}: "
                    f'{response.json().get("error",{}).get("message")}'
                )
                logger.debug(error)
                result["error"] = error
        except requests.exceptions.Timeout:
            error = "Could not connect to M42 (Timeout)"
            logger.debug(error)
            result["error"] = error
        return result

    def get_accesstoken(self) -> Dict[Text, Any]:        
        if self.userToken:
            logger.debug("Using existing token!")
            return self.userToken
        else:
            token_url = f"{self.base_api_url}/ApiToken/GenerateAccessTokenFromApiToken/"        
            headers = {
                    "Authorization": "Bearer " + self.M42_apitoken,
                    "Content-Type": "application/json"
                    }
            request_args = {
                "url": token_url,
                "headers": headers,   
            }
            
            result = self.handle_request(requests.post, request_args)
            logger.debug(result)
            self.userToken = result["content"]["RawToken"]
            return self.userToken

    def email_to_userid(self, email) -> Dict[Text, Any]:
        lookup_url = (
            f"{self.base_api_url}/data/fragments/SPSUserClassBase?where=MailAddress = '{email}'&columns=ID"
        )
        token = self.get_accesstoken()
        headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
                }
        request_args = {
            "url": lookup_url,            
            "headers": headers,
        }
        result = self.handle_request(requests.get, request_args)
        
        #user_id = result["content"][0]["ID"]
        logger.debug(result)
        
        try:
            result["user_id"] = result["content"][0]["ID"]
        except:
            result["user_id"] = []
            result["error"] = (
                f"Could not retrieve user id; "
                f"No records found for email {email}"
            )           
        
        return result

    def get_ticketNumber(
        self, ticket_id
    ) -> Dict[Text, Any]:
        
        if ticket_id:
            ticket_url = f"{self.base_api_url}/data/objects/SPSActivityTypeTicket/{ticket_id}"
            token = self.get_accesstoken()
            headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
                }
            request_args = {
                "url": ticket_url,
                "headers": headers,                
            }
            result = self.handle_request(requests.get, request_args)
            logger.debug(result)
            TicketNumber = result["content"]["SPSActivityClassBase"]["TicketNumber"]            
        return TicketNumber

    def retrieve_incidents(self, email) -> Dict[Text, Any]:
        result = self.email_to_userid(email)
        user_id = result.get("user_id")
        if user_id:
            incident_url = (
                f"{self.base_api_url}/incident/userincidents/{user_id}/0"                
            )
            token = self.get_accesstoken()
            headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
                }
            request_args = {
                "url": incident_url,            
                "headers": headers,
            }
            result = self.handle_request(requests.get, request_args)
            incidents = result.get(
                "content", {}  # pytype: disable=attribute-error
            ).get("result")
            if incidents:
                result["incidents"] = incidents
            elif isinstance(incidents, list):
                result["error"] = f"No incidents on record for {email}"
        return result

    def create_ticket(
        self, description, short_description, email
    ) -> Dict[Text, Any]:
        result = self.email_to_userid(email)
        user_id = result.get("user_id")
        if user_id:
            ticket_url = f"{self.base_api_url}/ticket/Create?activityType=5"
            data = {
                "JournalEntry": {
                    "Publish": 1,
                    "Comments": description,
                    "EntryType": 0,
                    "Creator": user_id,
                    "VisibleInPortal": 1,                    
                    "SkipRaiseCoRuEvent": 1,
                },
                "Subject": short_description,
                "Description": description,
                "User": user_id,
                "Creator": user_id,                
            }
            token = self.get_accesstoken()
            headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
                }
            request_args = {
                "url": ticket_url,
                "headers": headers,
                "data": json.dumps(data),
            }
            result = self.handle_request(requests.post, request_args)
            ticket_number = self.get_ticketNumber(result["content"])
        return ticket_number

    def search_faq(
        self, description
    ) -> Dict[Text, Any]:
    
        ticket_url = f"{self.base_api_url}/KBArticle/Search/?text={description}&operator=1&type=-1&state=144&MaxItemsCount=2"
        data = {                          
        }
        token = self.get_accesstoken()
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
            }
        request_args = {
            "url": ticket_url,
            "headers": headers,
            "data": json.dumps(data),
        }
        result = self.handle_request(requests.get, request_args)
        logger.debug(result)
        return result["content"]    

    

    @staticmethod
    def priority_db() -> Dict[str, int]:
        """Database of supported priorities"""
        priorities = {"low": 3, "medium": 2, "high": 1}
        return priorities