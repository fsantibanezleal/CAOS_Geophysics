"""Executing owned dataset route; parent explicitly installs reviewed assembly."""
from uuid import UUID

from fastapi import APIRouter,Depends,Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_dataset import create_owned_dataset
from app.magnetic_line_survey_dataset_accounting import DatasetBaseLedger,DeviceReservationLedger
from app.magnetic_line_survey_dataset_controller import WindowsPreparationController
from app.magnetic_line_survey_wire import WIRE_MAX_BYTES,parse_survey_dataset
from app.models import User
from app.projects import _owned_project


def install_magnetic_line_survey_dataset_routes(app,settings:Settings,current_user,get_session,*,
        controller:WindowsPreparationController,base_ledger:DatasetBaseLedger,device_ledger:DeviceReservationLedger):
    if not isinstance(controller,WindowsPreparationController) or not callable(base_ledger) or not callable(device_ledger):
        raise ValueError('Actual fixed preparation controller and complete ledgers are mandatory')
    router=APIRouter(prefix='/api/projects/{project_id}/magnetic-line-surveys',tags=['magnetic-line-surveys'])

    @router.post('/datasets',status_code=201)
    async def dataset(project_id:UUID,request:Request,user:User=Depends(current_user),session:AsyncSession=Depends(get_session)):
        await _owned_project(session,str(project_id),user)
        if request.headers.get('content-type','').split(';',1)[0].strip()!='application/json':
            raise ApiError(415,'mime_format_mismatch','Dataset request must be JSON')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>WIRE_MAX_BYTES:raise ApiError(422,'request_invalid','Dataset request exceeds its fixed byte limit',['body'])
            raw.extend(chunk)
        receipt=await create_owned_dataset(session,settings,user,project_id,parse_survey_dataset(bytes(raw)),
            controller=controller,base_ledger=base_ledger,device_ledger=device_ledger)
        return JSONResponse(receipt,status_code=201,headers={'Cache-Control':'no-store'})

    app.include_router(router)
