from integrator import LOGGER


class SimpleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        LOGGER.info(f"[tag: IAAAPI01] {request.method} - Request URL: {request.path}")
        LOGGER.info(f"[tag: IAAAPI03] Request Content-Type: {request.content_type}")

        # if request.GET:
        #     LOGGER.info(f'[tag: IAAAPI04] Request query params: {request.GET}')
        #
        # if request.POST:
        #     LOGGER.info(f'[tag: IAAAPI05] Request body: {request.POST}')
        #
        # if request.body:
        #     LOGGER.info(f'[tag: IAAAPI06] Request body: {request.body.decode("utf-8")}')
        #
        # if request.content_params:
        #     LOGGER.info(f'[tag: IAAAPI07] Request content params: {request.content_params}')

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        LOGGER.info(f"[tag: IAAAPI08] Status Code: {response.status_code}")
        # LOGGER.info(f'[tag: IAAAPI09] Response: {response.content}')

        return response
