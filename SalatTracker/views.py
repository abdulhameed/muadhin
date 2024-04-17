from rest_framework import viewsets
from .models import PrayerTime
from .serializers import PrayerTimeSerializer, DailyPrayerSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
import requests
from users.models import CustomUser, PrayerMethod
from .models import PrayerTime, DailyPrayer
from rest_framework.decorators import action
from django.utils import timezone


class DailyPrayerViewSet(viewsets.ModelViewSet):
    queryset = DailyPrayer.objects.all()
    serializer_class = DailyPrayerSerializer

    @action(detail=False, methods=['GET'])
    def get_daily_prayer_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            serializer = DailyPrayerSerializer(daily_prayer)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response("Daily prayer not found for the given user and date", status=404)


class PrayerTimeViewSet(viewsets.ModelViewSet):
    queryset = PrayerTime.objects.all()
    serializer_class = PrayerTimeSerializer

    @action(detail=False, methods=['GET'])
    def get_prayer_times_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            prayer_times = daily_prayer.prayertime_set.all()  # Assuming you have a related name for the reverse relationship in DailyPrayer model
            serializer = PrayerTimeSerializer(prayer_times, many=True)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response("Prayer times not found for the given user and date", status=404)

# class PrayerTimeViewSet(viewsets.ModelViewSet):
#     queryset = PrayerTime.objects.all()
#     serializer_class = PrayerTimeSerializer

#     @action(detail=False, methods=['GET'])
#     def get_prayer_times_for_user_and_day(self, request, user_id, prayer_date):
#         try:
#             prayer_times = PrayerTime.objects.filter(user=user_id, prayer_date=prayer_date)
#             serializer = PrayerTimeSerializer(prayer_times, many=True)
#             return Response(serializer.data)
#         except PrayerTime.DoesNotExist:
#             return Response("Prayer times not found for the given user and date", status=404)

# Endpoint for logged in user
# class PrayerTimeView(APIView):

#     def get(self, request):
#         user = request.user
#         prayer_method = PrayerMethod.objects.get(user=user)
#         date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))
        
#         api_url = "http://api.aladhan.com/v1/timingsByCity"
        
#         params = {
#             "date": date,
#             "city": user.city,  
#             "country": user.country,
#             "method": prayer_method.id,  
#         }

#         response = requests.get(api_url, params=params)

#         if response.status_code == 200:
#             data = response.json().get("data", {}).get("timings", {})
            
#             for prayer_name, prayer_time in data.items():
#                 prayer_time_obj, created = PrayerTime.objects.get_or_create(
#                     user=user,
#                     prayer_name=prayer_name,
#                     defaults={"prayer_time": datetime.strptime(prayer_time, '%H:%M')}
#                 )
#                 if not created:
#                     prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')  
#                     prayer_time_obj.save()
            
#         return Response(data)

    '''
    @parser_classes([JSONParser])
    class PrayerTimeView(APIView):

        def post(self, request):
            user = request.data.get('user')
            # Get user object
            user = CustomUser.objects.get(pk=user['id'])
            
            # Rest of the view code...
            
            return Response(data)


        POST /api/prayer-times/

    {
    "user": {
        "id": 1,
        "name": "John Doe"
    }
    }
    And access the user via request.data['user'] in the view code.
    '''


class PrayerTimeView(APIView):
    def get(self, request, user_id):
        user = CustomUser.objects.get(pk=user_id)
        prayer_method = PrayerMethod.objects.get(user=user)
        date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))

        api_url = "http://api.aladhan.com/v1/timingsByCity"

        params = {
            "date": date,
            "city": user.city,
            "country": user.country,
            "method": prayer_method.id,
        }

        response = requests.get(api_url, params=params)

        if response.status_code == 200:
            data = response.json().get("data", {}).get("timings", {})
            date_info = response.json()["data"]["date"]["gregorian"]
            gregorian_date = date_info['date']
            gregorian_weekday = date_info['weekday']['en']

            # Parse date
            gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")

            # Format to YYYY-MM-DD
            gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

            daily_prayer, created = DailyPrayer.objects.get_or_create(
                user=user,
                prayer_date=gregorian_date_formatted,
                defaults={
                    "weekday_name": gregorian_weekday,
                }
            )

            if not created:
                daily_prayer.weekday_name = gregorian_weekday
                daily_prayer.save()

            response_data = {
                "timings": data,
                "gregorian_date": gregorian_date,
                "gregorian_weekday": gregorian_weekday,
            }

            for prayer_name, prayer_time in data.items():
                prayer_time_obj, created = PrayerTime.objects.get_or_create(
                    daily_prayer=daily_prayer,
                    prayer_name=prayer_name,
                    defaults={
                        "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
                    }
                )

                if not created:
                    prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')
                    prayer_time_obj.save()

            return Response(response_data)
        else:
            return Response("Failed to fetch prayer times", status=400)
        
        
# class PrayerTimeView(APIView):

#     def get(self, request, user_id):
#         user = CustomUser.objects.get(pk=user_id)
#         prayer_method = PrayerMethod.objects.get(user=user)
#         date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))
        
#         api_url = "http://api.aladhan.com/v1/timingsByCity"
        
#         params = {
#             "date": date,
#             "city": user.city,  
#             "country": user.country,
#             "method": prayer_method.id,  
#         }

#         response = requests.get(api_url, params=params)

#         if response.status_code == 200:
#             print("<<<<<<<<<<>>>>>>>>>>>")
#             print(response.json().get("data", {}).get("date", {}).get("gregorian", {}).get("date", {}))
#             print(response.json().get("data", {}).get("date", {}).get("gregorian", {}).get("weekday", {}).get("en", {}))
#             data = response.json().get("data", {}).get("timings", {})
#             # date_info = data.get("data", {}).get("date", {}).get("gregorian", {})
#             date_info = response.json()["data"]["date"]["gregorian"]
#             # Extract gregorian date and weekday name
#             # gregorian_date = date_info.get("date")
#             gregorian_date = date_info['date']
#             gregorian_weekday = date_info['weekday']['en']
            
#             # Parse date 
#             gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")

#             # Format to YYYY-MM-DD
#             gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

#             # Create response data
#             response_data = {
#                 "timings": data,
#                 "gregorian_date": gregorian_date, 
#                 "gregorian_weekday": gregorian_weekday
#             }

#             for prayer_name, prayer_time in data.items():
#                 prayer_time_obj, created = PrayerTime.objects.get_or_create(
#                     user=user,
#                     prayer_name=prayer_name,
#                     defaults={
#                         "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
#                         "prayer_date": gregorian_date_formatted,
#                         "weekday_name": gregorian_weekday,
#                     }
#                 )
#                 if not created:
#                     prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')
#                     prayer_time_obj.prayer_date = gregorian_date_formatted
#                     prayer_time_obj.weekday_name = gregorian_weekday
#                     prayer_time_obj.save()
            
#         return Response(response_data)
    