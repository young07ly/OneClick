import ast
import jinja2
import os
import urllib2
import webapp2

from google.appengine.api import urlfetch

JINJA_ENVIRONMENT = jinja2.Environment(
    autoescape=True,
    extensions=['jinja2.ext.autoescape'],
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname('oneclick0827'), 'templates'))
)

class DashboardHandler(webapp2.RequestHandler):
    transaction_history_url = "http://api108094sandbox.gateway.akana.com/IVRCCMaintenanceREST/account/transactionHistory"
    transaction_history_hardcodedData = {
        "transactionIdentifier": "0f8fad5b-d9cb-469f-a165-70867728950e",
        "messageIdentifier": "0f8fad5b-d9cb-469f-a165-70867728950e",
        "messageDateTime": "1999-05-31T13:20:00-05:00",
        "messageSequenceIdentifier": "1",
        "requestorInfo": {
            "serverIdentifier": "IVR",
            "componentIdentifier": "IVRMISC",
            "userIdentifier": {
                "name": "CredCardActAppIDDev",
                "parameters": {
                    "nameValuePair": {
                        "name": "CertSubjectDN",
                        "value": "cn=Client,ou=USB.COM,o=ESD,l=St. Paul,st=MN,c=US"
                    }
                }
            }
        },
        "ccTranHistoryRequest": {
            "ivrIdentifierData": {
                "requestingApplicationName": "CCIVR",
                "clientSource": "I",
                "serviceVersion": "1.0",
                "requestIdentifier": "testcase10"
            },
            "ccTranHistoryRequestData": {
                "accountNumber": "4081840012169457",
                "requestType": "StatementMonth",
                "statementMonth": "10",
                "tranSequence": "Reverse",
                "authIndicator": "ExcludeAuth",
                "continueNumber": "1",
                "maxItems": "10000000"
            }
        }
    }

    def setMonetaryValue(self, json):
        for key, value in json.iteritems():
            if isinstance(value, float) or isinstance(value, int):
                json[key] = round(value, 2)
            elif isinstance(value, dict):
                self.setMonetaryValue(value)

        return json

    def monthly_processing(self, content):
        template_values = {
            'total_debit': 0,
            'total_credit': 0,
            'type_debit': {},
            'type_credit': {}
        }

        # Iteration
        for transaction in content:
            amount = float(transaction['TransactionAmount'])
            mcc_code = transaction['SICMCCCode']

            # Consolidate Credit / Debit
            if transaction.get('TransactionType') == 'Debit' and amount > 0:
                template_values['total_debit'] += amount
                if mcc_code in template_values['type_debit']:
                    value = template_values.get('type_debit')[mcc_code]
                    template_values.get('type_debit')[mcc_code] = value + amount
                else:
                    template_values.get('type_debit')[mcc_code] = amount

            elif transaction.get('TransactionType') == 'Credit' and amount > 0:
                template_values['total_credit'] += amount

                if mcc_code in template_values['type_credit']:
                    value = template_values.get('type_credit')[mcc_code]
                    template_values.get('type_credit')[mcc_code] = value + amount
                else:
                    template_values.get('type_credit')[mcc_code] = amount

        return template_values

    # TODO: Set as POST in the end
    def get(self):
        # Transaction History
        response = urlfetch.fetch(url=self.transaction_history_url,
                                  payload=self.transaction_history_hardcodedData,
                                  method=urlfetch.POST,
                                  headers={
                                      "Content-Type": "application/json",
                                      "Accept": "application/json"
                                  })

        if response.status_code == 200:
            # Content
            content = ast.literal_eval(response.content)\
                .get('CCTranHistoryResponseData')\
                .get('TransactionDetails')\
                .get('TransactionData')

            template_values = self.setMonetaryValue(self.monthly_processing(content))

            # template = JINJA_ENVIRONMENT.get_template('dashboard.html')
            # self.response.write(template.render(template_values))
            self.response.write(template_values)
        else:
            self.response.write("Error Code: " + response.status_code)

