from rest_framework import pagination


class DefaultPagination(pagination.PageNumberPagination):
    page_size_query_param = "limit"
