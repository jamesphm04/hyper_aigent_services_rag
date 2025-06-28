from dataclasses import dataclass

@dataclass
class AskRequestDTO:
    chatID: int
    question: str

@dataclass
class AnswerDTO:
    answer: str
    location: list[str]

@dataclass
class AskResponseDTO:
    status: str
    message: str
    data: list[AnswerDTO] = None