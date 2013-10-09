################################################################################
# Project     : AuShadha
# Description : Views for Patient addition, editing, deleting, JSON export and Search
# Author      : Dr.Easwar T.R , All Rights reserved with Dr.Easwar T.R.
# Date        : 16-09-2013
################################################################################


# General Module imports-----------------------------------
from datetime import datetime, date, time

# General Django Imports----------------------------------
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import RequestContext
#from django.core.context_processors import csrf
from django.contrib.auth.models import User

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from django.utils import simplejson
from django.core import serializers
from django.core.serializers import json
from django.core.serializers.json import DjangoJSONEncoder

from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required


# Application Specific Model Imports-----------------------
import AuShadha.settings as settings
from AuShadha.settings import APP_ROOT_URL
from AuShadha.core.serializers.data_grid import generate_json_for_datagrid
from AuShadha.core.views.dijit_tree import DijitTreeNode, DijitTree
from AuShadha.apps.ui.data.json import ModelInstanceJson
from AuShadha.apps.ui.data.summary import ModelInstanceSummary
from AuShadha.utilities.forms import aumodelformerrorformatter_factory
from AuShadha.apps.clinic.models import Clinic

from demographics.demographics.models import Demographics
from demographics.contact.models import Contact
from demographics.phone.models import Phone
from demographics.guardian.models import Guardian
from demographics.email_and_fax.models import EmailAndFax

from history.medical_history.models import MedicalHistory
from history.surgical_history.models import SurgicalHistory
from history.social_history.models import SocialHistory
from history.family_history.models import FamilyHistory
from history.obs_and_gyn.models import ObstetricHistoryDetail

from immunisation.models import Immunisation
from allergy_list.models import Allergy
from medication_list.models import MedicationList

from admission.models import AdmissionDetail, AdmissionDetailForm
from visit.models import VisitDetail, VisitImaging, VisitInv

from .models import PatientDetail, PatientDetailForm
from dijit_widgets.tree import PatientTree


# Views start here -----------------------------------------


@login_required
def patient_list(request):
    """View for Generating Patient List Takes on Request Object as argument."""
    user = request.user
    all_patients = PatientDetail.objects.all().order_by('first_name')
    variable = RequestContext(request, {'user': user,
                                        "all_patients": all_patients,
                                        "alternate_layout": False
                                        })
    return render_to_response('patient_detail/list.html', variable)


@login_required
def alternate_layout(request):
    """View for Generating an alternate layout for sandboxing purposes..."""
    user = request.user
    all_patients = PatientDetail.objects.all().order_by('first_name')
    variable = RequestContext(request, {'user': user,
                                        "all_patients": all_patients,
                                        "alternate_layout": True
                                        })
    return render_to_response('base_alternate.html', variable)


@login_required
def patient_index(request):
    """
    View for Generating Patient List.

    Takes on Request Object as argument.

    """
    user = request.user
    all_patients = PatientDetail.objects.all().order_by('patient_hospital_id')
    variable = RequestContext(request, {"all_patients": all_patients, 'user': user})
    return render_to_response('patient_detail/index.html', variable)


@login_required
def patient_detail_add(request, clinic_id = None):

    user = request.user
    print "Received a request to add a New Patient...."

    try:
      if clinic_id :
        clinic_id = int(clinic_id)
      else:
        clinic_id = int(request.GET.get('clinic_id'))
    except (KeyError,NameError,AttributeError,ValueError,TypeError):
        clinic_id = 1

    try:
      clinic = Clinic.objects.get(pk = clinic_id)          
      patient_detail_obj = PatientDetail(parent_clinic = clinic)
      if request.method == "GET" and request.is_ajax():
          patient_detail_form = PatientDetailForm(
              instance=patient_detail_obj)
          variable = RequestContext(request,
                                    {"user": user,
                                    "patient_detail_obj": patient_detail_obj,
                                    "patient_detail_form": patient_detail_form
                                    }
                                    )
          return render_to_response('patient_detail/add.html', variable)

      elif request.method == "POST"  and request.is_ajax():
          patient_detail_form = PatientDetailForm(request.POST,
                                                  instance = patient_detail_obj)
          if patient_detail_form.is_valid():
              saved_patient = patient_detail_form.save(commit = False)
              saved_patient.parent_clinic = clinic
              saved_patient.save()
              success = True
              json = return_patient_json(saved_patient,success)
          else:
              form_errors = aumodelformerrorformatter_factory(patient_detail_form)
              saved_patient = None
              success = False
              data = {'success':success,
                      'error_message':form_errors,
                      'form_errors': form_errors
                      }
              json = simplejson.dumps(data)

      else:
          raise Http404('Bad Request:: Unsupported Request Method.')

    except(Clinic.DoesNotExist):
        saved_patient = None
        success = False
        data = {'success':success,'error_message':"No Clinic by the specified id"}
        json = simplejson.dumps(data)

    return HttpResponse(json, content_type='application/json')




@login_required
def patient_detail_edit(request, id):
    if request.user:
        user = request.user
        if request.method == "GET" and request.is_ajax():
            try:
                id = int(id)
                patient_detail_obj = PatientDetail.objects.get(pk=id)
                patient_detail_edit_form = PatientDetailForm(
                    instance=patient_detail_obj)
                variable = RequestContext(request,
                                          {"user"   : user,
                                           "patient_detail_obj": patient_detail_obj,
                                           "patient_detail_edit_form"   : patient_detail_edit_form
                                           }
                                          )
            except TypeError or ValueError or AttributeError:
                raise Http404("BadRequest")
            except PatientDetail.DoesNotExist:
                raise Http404("BadRequest: Patient detail Data Does Not Exist")
            return render_to_response('patient_detail/edit.html', variable)
        elif request.method == 'POST' and request.is_ajax():
            try:
                id = int(id)
                patient_detail_obj = PatientDetail.objects.get(pk=id)
                patient_detail_edit_form = PatientDetailForm(
                    request.POST, instance=patient_detail_obj)
                if patient_detail_edit_form.is_valid():
                    detail_object = patient_detail_edit_form.save()
                    json = return_patient_json(detail_object, success=True)
                    #print json
                    return HttpResponse(json, content_type='application/json')
                else:
                    success = False
                    error_message = "Error:: Patient Detail could not be edited."
                    form_errors = ''
                    for error in patient_detail_edit_form.errors:
                        form_errors += '<p>' + error + '</p>'
                    json = return_patient_json(
                        detail_object=None, success=False)
                    return HttpResponse(json, content_type='application/json')
            except ValueError or AttributeError or TypeError:
                raise Http404("BadRequest: Server Error")
            except PatientDetail.DoesNotExist:
                raise Http404(
                    "BadRequest: Requested Patient detail DoesNotExist")
        else:
            raise Http404("BadRequest: Unsupported Request Method")


@login_required
def patient_detail_del(request, id):
    user = request.user
    if request.user and user.is_superuser:
        if request.method == "GET":
            try:
                id = int(id)
                patient_detail_obj = PatientDetail.objects.get(pk=id)
            except TypeError or ValueError or AttributeError:
                if request.is_ajax():
                    success = False
                    error_message = '''
                            ERROR!! Bad Request. Please refresh page and try again.
                           '''
                    data = {"success": success, "error_message": error_message}
                    json = simplejson.dumps(data)
                    return HttpResponse(json, content_type="application/json")
                else:
                    raise Http404("BadRequest")
            except PatientDetail.DoesNotExist:
                if request.is_ajax():
                    success = False
                    error_message = '''
                            ERROR!! Requested Patient Data Does not Exist.
                            Refresh Page and try again..
                           '''
                    data = {"success": success, "error_message": error_message}
                    json = simplejson.dumps(data)
                    return HttpResponse(json, content_type="application/json")
                else:
                    raise Http404(
                        "BadRequest: Patient detail Data Does Not Exist")
            if user.is_superuser:
                patient_detail_obj.delete()
                if request.is_ajax():
                    success = True
                    error_message = "Patient Deleted Successfully"
                    data = {"success": success, "error_message": error_message}
                    json = simplejson.dumps(data)
                    return HttpResponse(json, content_type="application/json")
                else:
                    return HttpResponseRedirect('/')
            else:
                if request.is_ajax():
                    success = False
                    error_message = "ERROR ! No Priviliges to Delete..."
                    data = {"success": success, "error_message": error_message}
                    json = simplejson.dumps(data)
                    return HttpResponse(json, content_type="application/json")
                else:
                    return HttpResponseRedirect('/')
        else:
            raise Http404("BadRequest: Unsupported Request Method")
    else:
        raise Http404("Server Error: No Permission to delete.")


def return_patient_json(patient,success = True):
   p = ModelInstanceJson(patient)
   return p()

@login_required
def render_patient_tree(request, patient_id=None):
    if request.method == "GET" and request.is_ajax():
      tree = PatientTree(request)()
      return HttpResponse(tree, content_type="application/json")
    else:
        raise Http404("Bad Request")


@login_required
def render_patient_summary(request, patient_id=None):
    if request.method == "GET" and request.is_ajax():
        user = request.user

        if patient_id:
            patient_id = int(patient_id)
        else:
            patient_id = int(request.GET.get('patient_id'))

        try:
            pat_obj = PatientDetail.objects.get(pk=patient_id)
            var = ModelInstanceSummary(pat_obj).variable
            var['user']  = user
            variable = RequestContext(request, var)
            return render_to_response('patient_detail/summary.html', variable)

        except(AttributeError, NameError, KeyError, TypeError, ValueError):
            raise Http404("ERROR! Bad Request Parameters")

        except(AttributeError, NameError, KeyError, TypeError, ValueError):
            raise Http404("ERROR! Requested Patient Data Does not exist")
    else:
        raise Http404("Bad Request")


def check_before_adding(patient_obj):
    patient_object = patient_obj
    patient_id = patient_object.patient_hospital_id
    all_patients = PatientDetail.objects.all()
    active_admissions = AdmissionDetail.objects.filter(
        patient_detail=patient_object).filter(admission_closed='False')
    active_visit = patient_object.has_active_visit()
    id_list = []
    for patient in all_patients:
        id_list.append(patient.patient_hospital_id)
    if patient_id in id_list:
        error = "This ID is already Taken. Please renter and retry"
        #print error
        return False
    else:
        if active_visit == False:
            if active_admissions == False:
                print 'All checked.. Everything ok.. '
                return True
            else:
                error = 'This patient has active admissions. Please discharge and retry.'
                #print error
                return False
        else:
            error = "This patient has active visit. Please discharge and retry."
            #print error
            return False



@login_required
def patient_id_autocompleter(request, patient_id=None):
    if request.method == "GET" and request.is_ajax():
        request_copy = request.GET.copy()
        if not patient_id:
            patient_id = request_copy.get('patient_id')
        else:
            patient_id = int(patient_id)
        patient_id_list = []
        if patient_id != "*":
            pat_obj = PatientDetail.objects.get(pk=patient_id)
            if pat_obj:
                dict_to_append = {}
                dict_to_append[
                    'patient_hospital_id'] = pat_obj.patient_hospital_id
                dict_to_append['patient_id'] = pat_obj.id
                dict_to_append['name'] = unicode(
                    pat_obj.patient_hospital_id) + "-" + pat_obj.__unicode__()
                dict_to_append['patient_name'] = pat_obj.__unicode__()
                dict_to_append['first_name'] = pat_obj.first_name
                dict_to_append['middle_name'] = pat_obj.middle_name
                dict_to_append['last_name'] = pat_obj.last_name
                dict_to_append['age'] = pat_obj.age
                dict_to_append['sex'] = pat_obj.sex
                patient_id_list.append(dict_to_append)
            else:
                dict_to_append = {"patient_name": "No-Result",
                                  "name": "No Patients Recorded.",
                                  "patient_id": "No-Result",
                                  "patient_hospital_id": "",
                                  "first_name": "",
                                  "middle_name": "",
                                  "last_name": "",
                                  "age": "",
                                  "sex": "",
                                  }
                patient_id_list.append(dict_to_append)
        else:
            dict_to_append = {"patient_name": "No-Result",
                              "name": "No Patients Recorded.",
                              "patient_id": "No-Result",
                              "patient_hospital_id": "",
                              "first_name": "",
                              "middle_name": "",
                              "last_name": "",
                              "age": "",
                              "sex": "",
                              }
            patient_id_list.append(dict_to_append)
        json = simplejson.dumps(patient_id_list)
        str_to_construct = simplejson.dumps(patient_id_list)
        f = open(
            os.path.join(settings.CUSTOM_SCRIPT_ROOT, 'patient_id_list.json'), 'w')
        f.write(str_to_construct)
        f.close()
        return HttpResponse(json, content_type='application/json')
    else:
        raise Http404("Bad Request..")


@login_required
def hospital_id_autocompleter(request, patient_hospital_id=None):

    if request.method == "GET" and request.is_ajax():
        request_copy = request.GET.copy()

        if not patient_hospital_id:
            hospital_id = request_copy.get('patient_hospital_id')
        else:
            hospital_id = unicode(patient_hospital_id)

        if hospital_id == "*":
            pat_obj = PatientDetail.objects.all()
        else:
            if hospital_id[-1:] == "*":
                hospital_id = hospital_id[:-1]
            pat_obj = PatientDetail.objects.filter(
                patient_hospital_id__startswith=hospital_id)
        hospital_id_list = []

        if pat_obj:
            for pat in pat_obj:
                dict_to_append = {}
                dict_to_append['patient_hospital_id'] = pat.patient_hospital_id
                dict_to_append['patient_id'] = pat.id
                dict_to_append['name'] = unicode(
                    pat.patient_hospital_id) + "-" + pat.__unicode__()
                dict_to_append['patient_name'] = pat.__unicode__()
                dict_to_append['first_name'] = pat.first_name
                dict_to_append['middle_name'] = pat.middle_name
                dict_to_append['last_name'] = pat.last_name
                dict_to_append['age'] = pat.age
                dict_to_append['sex'] = pat.sex
                hospital_id_list.append(dict_to_append)
        else:
            dict_to_append = {"patient_name": "No-Result",
                              "name": "No Patients Recorded.",
                              "patient_id": "No-Result",
                              "patient_hospital_id": "",
                              "first_name": "",
                              "middle_name": "",
                              "last_name": "",
                              "age": "",
                              "sex": "",
                              }
            hospital_id_list.append(dict_to_append)
        json = simplejson.dumps(hospital_id_list)

#    str_to_construct = "var PATIENT_LIST = " + str(hospital_id_list) +";"
        str_to_construct = simplejson.dumps(hospital_id_list)
        f = open(
            os.path.join(settings.CUSTOM_SCRIPT_ROOT, 'patient_list.json'), 'w')
        f.write(str_to_construct)
        f.close()
        return HttpResponse(json, content_type='application/json')
    else:
        raise Http404("Bad Request..")


@login_required
def patient_name_autocompleter(request, patient_name=None):

    if request.method == "GET" and request.is_ajax():
        request_copy = request.GET.copy()
        patient_name_list = []
        patient_id = None

        if request.GET.get('patient_id'):
            patient_id = int(request.GET.get('patient_id'))
        if not patient_name:
            patient_name = request_copy.get('patient_name')
        else:
            patient_name = unicode(patient_name)

        if patient_name == "*":
            pat_obj = PatientDetail.objects.all()
        else:
            if patient_name[-1:] == "*":
                patient_name = patient_name[:-1]
            if not patient_id:
                pat_obj = PatientDetail.objects.filter(
                    full_name__icontains=patient_name)
            else:
                pat_obj = PatientDetail.objects.filter(
                    full_name__icontains=patient_name).filter(pk=patient_id)

        if pat_obj:
            for pat in pat_obj:
                dict_to_append = {}
                dict_to_append['patient_id'] = pat.id
                dict_to_append['patient_hospital_id'] = pat.patient_hospital_id
                dict_to_append['patient_name'] = pat.full_name
                dict_to_append['first_name'] = pat.first_name
                dict_to_append['middle_name'] = pat.middle_name
                dict_to_append['last_name'] = pat.last_name
                dict_to_append['age'] = pat.age
                dict_to_append['sex'] = pat.sex
                patient_name_list.append(dict_to_append)
        else:
            dict_to_append = {"patient_name": "No-Result",
                              "name": "No Patients Recorded.",
                              "patient_id": "No-Result",
                              "patient_hospital_id": "",
                              "first_name": "",
                              "middle_name": "",
                              "last_name": "",
                              "age": "",
                              "sex": "",
                              }
            patient_name_list.append(dict_to_append)
        json = simplejson.dumps(patient_name_list)

        str_to_construct = simplejson.dumps(patient_name_list)
        f = open(
            os.path.join(settings.CUSTOM_SCRIPT_ROOT, 'patient_name_list.json'), 'w')
        f.write(str_to_construct)
        f.close()
        return HttpResponse(json, content_type='application/json')
    else:
        raise Http404("Bad Request..")




@login_required
def render_patient_list(request):
    """View for Generating Patient List Takes on Request Object as argument."""
    user = request.user
    data = []

    keys = ["sort( first_name)", "sort(-first_name)", "sort(+first_name)",
            "sort( last_name)", "sort(-last_name)", "sort(+last_name)",
            "sort( age)", "sort(-age)", "sort(+sex)",
            "sort( sex)", "sort(-sex)", "sort(+age)",
            "sort( patient_hospital_id)", "sort(-patient_hospital_id)",
            "sort(+patient_hospital_id)"
            ]
    key_sort_map = {
        "sort(+patient_hospital_id)": "patient_hospital_id",
        "sort( patient_hospital_id)": "patient_hospital_id",
        "sort(-patient_hospital_id)": "-patient_hospital_id",
        "sort(+first_name)": "first_name",
        "sort( first_name)": "first_name",
        "sort(-first_name)": "-first_name",
        "sort(+last_name)": "last_name",
        "sort( last_name)": "last_name",
        "sort(-last_name)": "-last_name",
        "sort(+sex)": "sex",
        "sort( sex)": "sex",
        "sort(-sex)": "-sex",
        "sort(+age)": "age",
        "sort( age)": "age",
        "sort(-age)": "-age",
    }

    search_field_list = ['id',
                         'patient_hospital_id',
                         'full_name',
                         'first_name',
                         'middle_name',
                         'last_name',
                         'age', 'sex',
                         'patient_id'
                         ]

    get_query_item_map = {'id': "pk",
                          'full_name': 'full_name',
                          'first_name': "first_name",
                          'middle_name': "middle_name",
                          'last_name': "last_name",
                          'patient_hospital_id': "patient_hospital_id",
                          'age': "age",
                          'sex': "sex",
                          'patient_id': "pk"
                          }

    def create_patient_list_json(all_p):

        if all_p is not None:

            data = []
            for patient in all_p:

                print "Evaluating Patient: "
                print patient

                #print "Generating URL for JSON export: "
                json = ModelInstanceJson(patient)()
                data.append(json)
        else:
          data = {}
        json = simplejson.dumps(data)
        #print json
        return HttpResponse(json, content_type="application/json")

    if request.GET.get('search_field') in search_field_list and \
       request.GET.get('search_for'):

        search_field = unicode(request.GET.get('search_field'))
        search_for = unicode(request.GET.get('search_for'))
        search_query_map = {
            "id": PatientDetail.objects.all(),
            "full_name": PatientDetail.objects.filter(full_name__icontains=search_for).order_by('first_name'),
            "first_name": PatientDetail.objects.filter(first_name__startswith=search_for),
            "middle_name": PatientDetail.objects.filter(middle_name__startswith=search_for),
            "last_name": PatientDetail.objects.filter(last_name__startswith=search_for),
            "age": PatientDetail.objects.filter(age__startswith=search_for),
            "sex": PatientDetail.objects.filter(sex__startswith=search_for),
            "patient_hospital_id": PatientDetail.objects.filter(patient_hospital_id__startswith=search_for),
        }

        if search_field != "id":

            if search_for == "*":
                print "Searching for ", search_field, " in All patients "
                all_patients = PatientDetail.objects.all()
            elif search_for[-1:] == "*":
                search_for = search_for[0:-1]
                print "Searching for ", search_field, \
                    " in patients filtered for", search_for
                all_patients = search_query_map[search_field]
            else:
                print "Searching for ", search_field, \
                    " in patients filtered for", search_for
                all_patients = search_query_map[search_field]
            return create_patient_list_json(all_patients)

        elif search_field == "id":
            if search_for == "*":
                print "Searching for ID in All Patients"
                all_patients = PatientDetail.objects.all()
                return create_patient_list_json(all_patients)
            elif search_for[-1:] == "*":
                print "Searching for ID in Patients starting with ", search_for[0:-1]
                search_for = int(search_for[0:-1])
                all_patients = search_query_map[search_field]
                return create_patient_list_json(all_patients)
            else:
                try:
                    search_for = int(search_for)
                    pat_obj = PatientDetail.objects.get(pk=search_for)
                    print "RETURNING PATIENT WITH ID: ", search_for, "--", pat_obj
                    json = return_patient_json(pat_obj)
                    return HttpResponse(json, content_type="application/json")
                except(ValueError, TypeError, NameError, KeyError, AttributeError):
                    raise Http404("ERROR! Invalid request Parameters")
                except(PatientDetail.DoesNotExist):
                    raise Http404("ERROR! No Patient Data Found. ")

    else:
        raise Http404("ERROR! Invalid Search parameters")


@login_required
def patient_filtering_search_json(request, id=None):
# FIXME Dojo sends REST queries with * suffix. This has to be split and dealt with before json generation is done.
# Right now whatever you search for will not get results.
    if request.method == "GET" and request.is_ajax():
        if not id:
            try:
                name = unicode(request.GET.get('name'))
                print "You have queried Patients with Full Name containing: ", name
            except(TypeError, ValueError, NameError, KeyError):
                raise Http404(
                    "Bad Parameters.. No Search Results Could be returned. ")
            if name == "*":
                pat_obj = PatientDetail.objects.all()
            elif name[-1:] == "*":
                name = name[0:-1]
                print "Name after stripping trailing '*' is: ", name
                pat_obj = PatientDetail.objects.filter(
                    full_name__icontains=name)
            else:
                pat_obj = PatientDetail.objects.filter(
                    full_name__icontains=name)
            json = []
            if pat_obj:
                for patient in pat_obj:
                    data_to_append = {}
                    data_to_append['name'] = patient.full_name
                    data_to_append['id'] = patient.id
                    data_to_append['hospital_id'] = patient.patient_hospital_id
                    data_to_append['age'] = patient.age
                    data_to_append['sex'] = patient.sex
                    data_to_append['label'] = patient.full_name + "-" + \
                        patient.age       + "/" + \
                        patient.sex       + "(" + \
                        patient.patient_hospital_id + ")"
                    json.append(data_to_append)
            json = simplejson.dumps(json)
            return HttpResponse(json, content_type="application/json")
        elif id:
            try:
                id = int(id)
                pat_obj = PatientDetail.objects.get(pk=id)
            except(TypeError, KeyError, NameError, AttributeError):
                raise Http404("ERROR ! Bad Parameters. No Patients in result.")
            except(PatientDetail.DoesNotExist):
                raise Http404("ERROR! Patient Does Not Exist")
            json = return_patient_json(pat_obj)
            return HttpResponse(json, content_type="application/json")
    else:
        raise Http404("Bad Request")

@login_required
def patient_search(request, search_by, search_for):
    if request.user:
        user = request.user
        search_by = request.GET['search_by']
        search_for = request.GET['search_for']

        if search_by == "first_name":
            try:
                patient_obj = PatientDetail.objects.filter(
                    first_name__icontains=search_for)
                variable = RequestContext(
                    request, {'patient_obj': patient_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "middle_name":
            try:
                patient_obj = PatientDetail.objects.filter(
                    middle_name__icontains=search_for)
                variable = RequestContext(
                    request, {'patient_obj': patient_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "last_name":
            try:
                patient_obj = PatientDetail.objects.filter(
                    last_name__icontains=search_for)
                variable = RequestContext(
                    request, {'patient_obj': patient_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "hospital_id":
            try:
                patient_obj = PatientDetail.objects.filter(
                    patient_hospital_id__icontains=search_for)
                variable = RequestContext(
                    request, {'patient_obj': patient_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "phone":
            try:
                phone_obj = Phone.objects.filter(
                    phone__icontains=search_for)
                variable = RequestContext(
                    request, {'phone_obj': phone_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "guardian_name":
            try:
                guardian_obj = Guardian.objects.filter(
                    guardian_name__icontains=search_for)
                variable = RequestContext(
                    request, {'guardian_obj': guardian_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

        elif search_by == "city":
            try:
                contact_obj = Contact.objects.filter(
                    city__icontains=search_for)
                variable = RequestContext(
                    request, {'contact_obj': contact_obj, 'user': user})
                return render_to_response('patient/patient_search_result.html', variable)
            except ValueError or TypeError or AttributeError:
                raise Http404("Please enter a correct search term")

    else:
        raise Http404("Please Log in")