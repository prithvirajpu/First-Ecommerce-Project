from django.utils.deprecation import MiddlewareMixin

class DisableCacheMiddleware(MiddlewareMixin): 
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
