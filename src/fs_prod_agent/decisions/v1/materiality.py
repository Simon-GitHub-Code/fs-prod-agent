from fs_prod_agent.decisions.contract import Question
from fs_prod_agent.decisions.v1.route import INGRESS_QUESTIONS

# Asked by the application after mandate_check returns, not inside the calculator.
MATERIALITY_QUESTIONS: list[Question] = [question for question in INGRESS_QUESTIONS if question.id == "materiality"]
