from dataclasses import dataclass

@dataclass
class AskRequestDTO:
    fileID: int
    question: str

@dataclass
class AnswerDTO:
    answer: str
    location: list[str]

@dataclass
class AskResponseDTO:
    status: str
    message: str
    task_id: str = None
    data: list[AnswerDTO] = None