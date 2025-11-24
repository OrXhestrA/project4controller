from fastapi import APIRouter, HTTPException
from app.models import (
    HeartDataRequest, HeartDataResponse,
    VideoDataRequest, VideoDataResponse,
    UserDataRequest, UserDataResponse,
    BioDataRequest, BioDataResponse,
    PredictAllResponse,
    SetPredictParamsRequest,
    PredictByUserIdRequest, PredictByUserIdResponse,
    GenericResponse
)
from app.services import data_service, predict_service
from app.utils import log

router = APIRouter()


@router.post(
    "/upload_heart_data",
    response_model=HeartDataResponse,
    tags=["Data Upload"],
    summary="上传心率数据"
)
async def upload_heart_data(request: HeartDataRequest) -> HeartDataResponse:
    log.info(f"Upload heart data: {request.user_id}")
    return await data_service.upload_heart_data(request=request)


@router.post(
    "/test_post",
    tags=["Test"],
    summary="测试post"
)
async def test_post(request: HeartDataRequest):
    return request.heart_rate


@router.post(
    "/upload_video_data",
    response_model=VideoDataResponse,
    tags=["Data Upload"],
    summary="上传视频数据"
)
async def upload_video_data(request: VideoDataRequest) -> VideoDataResponse:
    return await data_service.upload_video_data(request=request)


@router.post(
    "/upload_user_data",
    response_model=UserDataResponse,
    tags=["Data Upload"],
    summary="上传用户数据"
)
async def upload_user_data(request: UserDataRequest) -> UserDataResponse:
    return await data_service.upload_user_data(request=request)


@router.post(
    "/upload_bio_data",
    response_model=BioDataResponse,
    tags=["Data Upload"],
    summary="上传生物数据"
)
async def upload_bio_data(request: BioDataRequest) -> BioDataResponse:
    return await data_service.upload_bio_data(request=request)


@router.get(
    "/predict_all",
    response_model=PredictAllResponse,
    tags=["Predict"],
    summary="预测所有用户"
)
async def predict_all():
    """Predict All activate users current status"""
    try:
        results = await predict_service.predict_all()
        return PredictAllResponse(result=results)
    except Exception as e:
        log.error(f"All predict failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/set_params",
    response_model=PredictByUserIdRequest,
    tags=["Predict"],
    summary="设置预测参数"
)
async def set_predict_params(request: SetPredictParamsRequest) -> GenericResponse:
    """
    Set Model predict parameters.
    :param request: params
    :return:
    """
    try:
        if not all(m in [0, 1] for m in request.models):
            raise HTTPException(status_code=400, detail="Invalid model value")

        if not all(0 <= t <= 1 for t in request.thresholds):
            raise HTTPException(status_code=400, detail="Invalid threshold value")

        params = {
            "current_timestamp": request.current_timestamp,
            "predict_time_length": request.predict_time_length,
            "thresholds": request.thresholds,
            "models": request.models
        }
        predict_service.set_predict_params(params)

        return GenericResponse(message="Predict params updated")
    except Exception as e:
        log.error(f"Set predict params failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/predict_by_userId",
    response_model=PredictByUserIdResponse,
    tags=["Predict"],
    summary="预测指定用户"
)
async def predict_by_user_ids(request: PredictByUserIdRequest) -> PredictByUserIdResponse:
    """
    Predict by user ids.
    :param request: user_ids
    :return:
    """
    try:
        if not all(m in [0, 1] for m in request.models):
            raise HTTPException(status_code=400, detail="Invalid model value")

        if not all(0 <= t <= 1 for t in request.thresholds):
            raise HTTPException(status_code=400, detail="Invalid threshold value")

        results = await predict_service.predict_by_user_ids(
            user_ids=request.user_ids,
            thresholds=request.thresholds,
            models=request.models
        )

        return PredictByUserIdResponse(result=results)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Predict by user ids failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

