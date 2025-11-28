from fastapi import (
    APIRouter,
    HTTPException,
    File,
    UploadFile,
    Form
)
from app.models.request import (
    HeartDataRequest,
    VideoUploadRequest,
    BioDataRequest,
    UserDataRequest,
    SetParamsRequest,
    PredictRequest
)
from app.models.response import (
    HeartDataResponse,
    VideoDataResponse,
    UserDataResponse,
    BioDataResponse,
    PredictResponse,
    GenericResponse
)
from app.services.storage_service import StorageService
from app.services.predict_service import ModelInterface
from app.utils.logger import log
from app.config.base_config import settings

router = APIRouter()


@router.post(
    "/upload_heart_data",
    response_model=HeartDataResponse,
    tags=["Data Upload"],
    summary="上传心率数据"
)
async def upload_heart_data(request: HeartDataRequest) -> HeartDataResponse:
    log.info(f"Upload heart data: {request.user_id}")
    return await StorageService.upload_heart_data(request=request)


@router.post(
    "/upload_video_data",
    response_model=VideoDataResponse,
    tags=["Data Upload"],
    summary="上传视频数据"
)
async def upload_video_data(request: VideoUploadRequest) -> VideoDataResponse:
    log.info(f"Upload video data: {request.user_id}")
    # TODO
    return await StorageService.upload_video_data(request=request)


@router.post(
    "/upload_user_data",
    response_model=UserDataResponse,
    tags=["Data Upload"],
    summary="上传用户数据"
)
async def upload_user_data(request: UserDataRequest) -> UserDataResponse:
    log.info(f"Upload user data: {request.user_id}")
    return await StorageService.upload_user_data(request=request)


@router.post(
    "/upload_bio_data",
    response_model=BioDataResponse,
    tags=["Data Upload"],
    summary="上传生物数据"
)
async def upload_bio_data(request: BioDataRequest) -> BioDataResponse:
    log.info(f"Upload bio data: {request.user_id}")
    return await StorageService.upload_bio_data(request=request)


@router.post(
    "/set_params",
    response_model=GenericResponse,
    tags=["Data Upload"],
    summary="设置参数"
)
async def set_parameters(request: SetParamsRequest) -> GenericResponse:
    log.info(f"Set parameters: {request.user_id}")
    try:
        settings.DEFAULT_THRESHOLDS = request.thresholds
        settings.DEFAULT_MODELS = request.models
        settings.DEFAULT_PREDICT_TIME_LENGTH = request.predict_time_length
        return GenericResponse()
    except Exception as e:
        log.error(f"Error when set parameters: {e}")
        raise HTTPException(status_code=500, detail="Error when set parameters")


@router.post(
    "/predict_by_userIds",
    response_model=PredictResponse,
    tags=["Predict"],
    summary="预测指定用户"
)
async def predict_by_user_ids(request: PredictRequest) -> PredictResponse:
    log.info(f"Predict by user ids: {request.user_ids}")
    try:
        result = await ModelInterface.predict(request.user_ids)
        log.info(f"Predict result: {result}")
        return PredictResponse(predict_results=result)
    except Exception as e:
        log.error(f"Error when predict by user ids: {e}")
        raise HTTPException(status_code=500, detail="Error when predict by user ids")
