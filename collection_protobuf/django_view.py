from django.views.generic.base import View
from django import http
from abc import ABCMeta, abstractproperty, abstractmethod


class ServiceView(View):
    __metaclass__ = ABCMeta
    content_type = "application/vnd.collection+protobuf"

    @abstractproperty
    def _service(self):
        pass

    @abstractmethod
    def _query(self, request, *args, **kwargs):
        pass

    @abstractproperty
    def _profile_href(self):
        pass

    @abstractproperty
    def _href(self):
        pass

    @abstractmethod
    def _item_href(self, item, model):
        pass

    @property
    def service(self):
        s = self._service
        s.item_hooks.add(self._item)
        return s
        
    def _item(self, item, model):
        item.href = self._item_href(item, model)

    def _resource(self, resource):
        resource.collection.href = self._href

    ###================================================================
    ### Render methods
    ###================================================================
    def get(self, request, *args, **kwargs):
        result = self._query(request, *args, **kwargs)
        return self.render(
            accept(request),
            result)

    def put(self, request, *args, **kwargs):
        result = self._query(request, *args, **kwargs)
        
        if result.status == 200:
            result = self.service.store_bytes(request.body)

        return self.render(
            accept(request),
            result)

    def post(self, request, *args, **kwargs):
        result = self.service.store_bytes(request.body)
        return self.render(
            accept(request),
            result)

    ###================================================================
    ### Render methods
    ###================================================================
    def render_text(self, result):
        return http.HttpResponse(
            unicode(result.resource),
            content_type="text/plain",
            status=result.status)

    def render_pb(self, result):
        full_content_type = self.content_type + "; profile=" + self._profile_href
        return http.HttpResponse(
            result.resource.SerializeToString(),
            content_type=full_content_type,
            status=result.status)

    def render_no_content(self):
        return http.HttpResponse(
            '',
            status=204)

    def render(self, accept, result):
        if result.status == 204:
            return self.render_no_content()

        self._resource(result.resource)

        response = self.select_response(accept, result)
        response['link'] = '<{0}>; rel="profile"'.format(self._profile_href)
        return response

    def select_response(self, accept, result):
        if accept_matches(accept, "text/plain"):
            return self.render_text(result)
        else:
            return self.render_pb(result)


def accept_matches(accept, media_type):
    # TODO: add better accept handling
    return accept == media_type

def accept(request):
    return request.META.get("HTTP_ACCEPT", "")
