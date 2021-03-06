import datetime

from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.template.loader import get_template
from django.template.context import Context
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.text import Truncator

from exadmin.views.list import EMPTY_CHANGELIST_VALUE

FILTER_PREFIX = '_p_'
SEARCH_VAR = '_q_'

from util import (get_model_from_relation,
    reverse_field_path, get_limit_choices_to_from_path, prepare_lookup_value)

class BaseFilter(object):
    title = None
    template = 'admin/filters/list.html'

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        pass

    def __init__(self, request, params, model, admin_view):
        self.used_params = {}
        self.request = request
        self.params = params
        self.model = model
        self.admin_view = admin_view

        if self.title is None:
            raise ImproperlyConfigured(
                "The filter '%s' does not specify "
                "a 'title'." % self.__class__.__name__)

    def query_string(self, new_params=None, remove=None):
        return self.admin_view.get_query_string(new_params, remove)

    def form_params(self):
        return self.admin_view.get_form_params(\
            remove=map(lambda k: FILTER_PREFIX+k, self.used_params.keys()))

    def has_output(self):
        """
        Returns True if some choices would be output for this filter.
        """
        raise NotImplementedError

    @property
    def is_used(self):
        return len(self.used_params) > 0

    def do_filte(self, queryset):
        """
        Returns the filtered queryset.
        """
        raise NotImplementedError

    def get_context(self):
        return {'title': self.title, 'spec': self, 'form_params': self.form_params()}

    def __repr__(self):
        tpl = get_template(self.template)
        return mark_safe(tpl.render(Context(self.get_context())))

class FieldFilterManager(object):
    _field_list_filters = []
    _take_priority_index = 0

    def register(self, list_filter_class, take_priority=False):
        if take_priority:
            # This is to allow overriding the default filters for certain types
            # of fields with some custom filters. The first found in the list
            # is used in priority.
            self._field_list_filters.insert(
                self._take_priority_index, list_filter_class)
            self._take_priority_index += 1
        else:
            self._field_list_filters.append(list_filter_class)
        return list_filter_class

    def create(self, field, request, params, model, admin_view, field_path):
        for list_filter_class in self._field_list_filters:
            if not list_filter_class.test(field, request, params, model, admin_view, field_path):
                continue
            return list_filter_class(field, request, params,
                model, admin_view, field_path=field_path)

manager = FieldFilterManager()

class FieldFilter(BaseFilter):

    lookup_formats = {}

    def __init__(self, field, request, params, model, admin_view, field_path):
        self.field = field
        self.field_path = field_path
        self.title = getattr(field, 'verbose_name', field_path)
        self.context_params = {}

        super(FieldFilter, self).__init__(request, params, model, admin_view)

        for name, format in self.lookup_formats.items():
            p = format % field_path
            self.context_params["%s_name" % name] = FILTER_PREFIX + p
            if p in params:
                value = prepare_lookup_value(p, params.pop(p))
                self.used_params[p] = value
                self.context_params["%s_val" % name] = value
            else:
                self.context_params["%s_val" % name] = ''

        map(lambda kv: setattr(self, 'lookup_' + kv[0], kv[1]), self.context_params.items())

    def get_context(self):
        context = super(FieldFilter, self).get_context()
        context.update(self.context_params)
        context['remove_url'] = self.query_string({}, map(lambda k:FILTER_PREFIX + k, self.used_params.keys()))
        return context

    def has_output(self):
        return True

    def do_filte(self, queryset):
        return queryset.filter(**self.used_params)

class ListFieldFilter(FieldFilter):
    template = 'admin/filters/list.html'

    def get_context(self):
        context = super(ListFieldFilter, self).get_context()
        context['choices'] = list(self.choices())
        return context

@manager.register
class BooleanFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact', 'isnull': '%s__isnull'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, (models.BooleanField, models.NullBooleanField))

    def choices(self):
        for lookup, title in (
                ('', _('All')),
                ('1', _('Yes')),
                ('0', _('No'))):
            yield {
                'selected': self.lookup_exact_val == lookup and not self.lookup_isnull_val,
                'query_string': self.query_string({
                        self.lookup_exact_name: lookup,
                    }, [self.lookup_isnull_name]),
                'display': title,
            }
        if isinstance(self.field, models.NullBooleanField):
            yield {
                'selected': self.lookup_isnull_val == 'True',
                'query_string': self.query_string({
                        self.lookup_isnull_name: 'True',
                    }, [self.lookup_exact_name]),
                'display': _('Unknown'),
            }

@manager.register
class ChoicesFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return bool(field.choices)

    def choices(self):
        yield {
            'selected': self.lookup_exact_val is '',
            'query_string': self.query_string({}, [self.lookup_exact_name]),
            'display': _('All')
        }
        for lookup, title in self.field.flatchoices:
            yield {
                'selected': smart_unicode(lookup) == self.lookup_exact_val,
                'query_string': self.query_string({self.lookup_exact_name: lookup}),
                'display': title,
            }

@manager.register
class TextFieldListFilter(FieldFilter):
    template = 'admin/filters/char.html'
    lookup_formats = {'search':'%s__contains'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return (isinstance(field, models.CharField) and field.max_length > 20) or isinstance(field, models.TextField)

@manager.register
class NumberFieldListFilter(FieldFilter):
    template = 'admin/filters/number.html'
    lookup_formats = {'equal':'%s__exact', 'lt': '%s__lt', 'gt': '%s__gt',
        'ne':'%s__ne', 'lte': '%s__lte', 'gte': '%s__gte',
    }

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, (models.DecimalField, models.FloatField, models.IntegerField))

    def do_filte(self, queryset):
        params = self.used_params.copy()
        ne_key = '%s__ne' % self.field_path
        if params.has_key(ne_key):
            queryset = queryset.exclude(**{self.field_path: params.pop(ne_key)})
        return queryset.filter(**params)

@manager.register
class DateFieldListFilter(ListFieldFilter):
    template = 'admin/filters/date.html'
    lookup_formats = {'since': '%s__gte', 'until': '%s__lt', 
        'year': '%s__year', 'month': '%s__month', 'day': '%s__day'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, models.DateField)

    def __init__(self, field, request, params, model, admin_view, field_path):
        self.field_generic = '%s__' % field_path
        self.date_params = dict([(FILTER_PREFIX + k, v) for k, v in params.items()
                                 if k.startswith(self.field_generic)])

        super(DateFieldListFilter, self).__init__(
            field, request, params, model, admin_view, field_path)

        now = timezone.now()
        # When time zone support is enabled, convert "now" to the user's time
        # zone so Django's definition of "Today" matches what the user expects.
        if now.tzinfo is not None:
            current_tz = timezone.get_current_timezone()
            now = now.astimezone(current_tz)
            if hasattr(current_tz, 'normalize'):
                # available for pytz time zones
                now = current_tz.normalize(now)

        if isinstance(field, models.DateTimeField):
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:       # field is a models.DateField
            today = now.date()
        tomorrow = today + datetime.timedelta(days=1)
    
        self.links = (
            (_('Any date'), {}),
            (_('Today'), {
                self.lookup_since_name: str(today),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('Past 7 days'), {
                self.lookup_since_name: str(today - datetime.timedelta(days=7)),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('This month'), {
                self.lookup_since_name: str(today.replace(day=1)),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('This year'), {
                self.lookup_since_name: str(today.replace(month=1, day=1)),
                self.lookup_until_name: str(tomorrow),
            }),
        )

    def get_context(self):
        context = super(DateFieldListFilter, self).get_context()
        context['choice_selected'] = bool(self.lookup_year_val) or bool(self.lookup_month_val) \
            or bool(self.lookup_day_val)
        return context

    def choices(self):
        for title, param_dict in self.links:
            yield {
                'selected': self.date_params == param_dict,
                'query_string': self.query_string(
                                    param_dict, [FILTER_PREFIX + self.field_generic]),
                'display': title,
            }

@manager.register
class RelatedFieldSearchFilter(FieldFilter):
    template = 'admin/filters/fk_search.html'

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        if not (hasattr(field, 'rel') and bool(field.rel) or isinstance(field, models.related.RelatedObject)):
            return False
        related_modeladmin = admin_view.admin_site._registry.get(get_model_from_relation(field))
        return related_modeladmin and getattr(related_modeladmin, 'relfield_style', None) == 'fk-ajax'

    def __init__(self, field, request, params, model, model_admin, field_path):
        other_model = get_model_from_relation(field)
        if hasattr(field, 'rel'):
            rel_name = field.rel.get_related_field().name
        else:
            rel_name = other_model._meta.pk.name

        self.lookup_formats = {'exact': '%%s__%s__exact' % rel_name}
        super(RelatedFieldSearchFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        if hasattr(field, 'verbose_name'):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        self.title = self.lookup_title
        self.search_url = model_admin.get_admin_url('%s_%s_changelist' % (other_model._meta.app_label, other_model._meta.module_name))
        self.label = self.label_for_value(other_model, rel_name, self.lookup_exact_val) if self.lookup_exact_val else ""

    def label_for_value(self, other_model, rel_name, value):
        try:
            obj = other_model._default_manager.get(**{rel_name: value})
            return '%s' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, other_model.DoesNotExist):
            return ""

    def get_context(self):
        context = super(RelatedFieldSearchFilter, self).get_context()
        context['search_url'] = self.search_url
        context['label'] = self.label
        return context


@manager.register
class RelatedFieldListFilter(ListFieldFilter):

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return (hasattr(field, 'rel') and bool(field.rel) or isinstance(field, models.related.RelatedObject))

    def __init__(self, field, request, params, model, model_admin, field_path):
        other_model = get_model_from_relation(field)
        if hasattr(field, 'rel'):
            rel_name = field.rel.get_related_field().name
        else:
            rel_name = other_model._meta.pk.name

        self.lookup_formats = {'exact': '%%s__%s__exact' % rel_name, 'isnull': '%s__isnull'}
        self.lookup_choices = field.get_choices(include_blank=False)
        super(RelatedFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        if hasattr(field, 'verbose_name'):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        self.title = self.lookup_title

    def has_output(self):
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                    and self.field.null):
            extra = 1
        else:
            extra = 0
        return len(self.lookup_choices) + extra > 1

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def choices(self):
        yield {
            'selected': self.lookup_exact_val == '' and not self.lookup_isnull_val,
            'query_string': self.query_string({},
                [self.lookup_exact_name, self.lookup_isnull_name]),
            'display': _('All'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_exact_val == smart_unicode(pk_val),
                'query_string': self.query_string({
                    self.lookup_exact_name: pk_val,
                }, [self.lookup_isnull_name]),
                'display': val,
            }
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                    and self.field.null):
            yield {
                'selected': bool(self.lookup_isnull_val),
                'query_string': self.query_string({
                    self.lookup_isnull_name: 'True',
                }, [self.lookup_exact_name]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

@manager.register
class AllValuesFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact', 'isnull': '%s__isnull'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return True

    def __init__(self, field, request, params, model, admin_view, field_path):
        parent_model, reverse_path = reverse_field_path(model, field_path)
        queryset = parent_model._default_manager.all()
        # optional feature: limit choices base on existing relationships
        # queryset = queryset.complex_filter(
        #    {'%s__isnull' % reverse_path: False})
        limit_choices_to = get_limit_choices_to_from_path(model, field_path)
        queryset = queryset.filter(limit_choices_to)

        self.lookup_choices = (queryset
                               .distinct()
                               .order_by(field.name)
                               .values_list(field.name, flat=True))
        super(AllValuesFieldListFilter, self).__init__(
            field, request, params, model, admin_view, field_path)

    def choices(self):
        yield {
            'selected': (self.lookup_exact_val is '' and self.lookup_isnull_val is ''),
            'query_string': self.query_string({}, [self.lookup_exact_name, self.lookup_isnull_name]),
            'display': _('All'),
        }
        include_none = False
        for val in self.lookup_choices:
            if val is None:
                include_none = True
                continue
            val = smart_unicode(val)
            yield {
                'selected': self.lookup_exact_val == val,
                'query_string': self.query_string({self.lookup_exact_name: val}, 
                    [self.lookup_isnull_name]),
                'display': val,
            }
        if include_none:
            yield {
                'selected': bool(self.lookup_isnull_val),
                'query_string': self.query_string({self.lookup_isnull_name: 'True'}, 
                    [self.lookup_exact_name]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

