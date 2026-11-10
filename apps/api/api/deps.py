from typing import Annotated

from fastapi import Depends, Request

from agent.services.turns import TurnService


def get_turn_service(request: Request) -> TurnService:
    return request.app.state.turn_service


TurnServiceDep = Annotated[TurnService, Depends(get_turn_service)]
