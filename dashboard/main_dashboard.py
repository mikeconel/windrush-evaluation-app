# dashboard/main.py
# dashboard/main.py
from django.db.models import Count, Q, Avg, Max, Min
import streamlit as st
import pandas as pd
import plotly.express as px
from textblob import TextBlob
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os
import sys
from PIL import Image
from datetime import datetime
#import nltk
#nltk.download('punkt')
#from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.exceptions import ObjectDoesNotExist

# Load images

#logo = "dashboard/images/Windrush logo clipped1_redrawn BLUEE_v2 3_R1.png"
logo = "dashboard/images/Windrush Logo White_30th Anniversary_2025.png"
logo_path = Image.open(logo) 
logo2 = "dashboard/images/Windrush Foundation 30th Anniversary 2025_R4.png"
logo_path_2 = Image.open(logo2)

# Configure Django environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_dir = os.path.join(project_root, "backend")

sys.path.extend([project_root, backend_dir])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from evaluations.models import Participant, Response, Question, EvaluationSession

# ========================
# CACHED DATA FUNCTIONS
# ========================

@st.cache_data(ttl=3600)
def get_public_data():
    """Aggregate public-facing data"""
    return {
        'participants': Participant.objects.values('gender', 'ethnicity', 'age'),
        'responses': Response.objects.values('question__text', 'answer'),
        'sessions': EvaluationSession.objects.filter(completed=True)
    }

@st.cache_data(ttl=300)
def get_private_data():
    """Secure sensitive data access"""
    if st.session_state.get('authenticated'):
        return {
            'participants': pd.DataFrame(list(Participant.objects.all().values())),
            'responses': pd.DataFrame(list(Response.objects.all().values())),
            'sessions': EvaluationSession.objects.all()
        }
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_geospatial_data():
    """Cache geocoding results"""
    postcodes = Participant.objects.exclude(postcode__exact='').values_list('postcode', flat=True).distinct()
    
    geolocator = Nominatim(user_agent="windrush_geo")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    
    locations = []
    for postcode in postcodes:
        try:
            location = geocode(postcode)
            if location:
                locations.append({
                    "postcode": postcode,
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "count": Participant.objects.filter(postcode=postcode).count()
                })
        except Exception as e:
            continue
    return pd.DataFrame(locations)

# ========================
# VISUALIZATION COMPONENTS
# ========================

def show_public_components(data):
    """Public-facing components"""
    session_key = st.experimental_get_query_params().get('session_key', [None])[0]
    if session_key:
        st.title(':blue[Thank You for Participating!]')
        st.markdown(f"<div style='font-weight:bold'>Your responses will help us improve future events.</div>",unsafe_allow_html=True)
        st.markdown(f"<p style='font-weight:bold'>For more Windrush Foundation events, check out our website:<a href='https://www.windrushfoundation.com/'><h5>www.windrushfoundation.com</h></a></p>",unsafe_allow_html=True)


    # Word Cloud
    with st.container():
        st.markdown("<h5 style='color:blue;font-weight:bold'>Community Feedback Overview</h5>", 
                   unsafe_allow_html=True)
        feedback_data = Response.objects.filter(question__question_type='TX').values_list('answer', flat=True)
        if feedback_data:
            text = ' '.join([d for d in feedback_data if isinstance(d, str)])
            wordcloud = WordCloud(width=2400, height=600).generate(text) #1700
            st.image(wordcloud.to_array(), caption="Most Frequent Feedback Terms")
        else:
            st.info("No text feedback available yet")


def handle_dates():
    """Central date range handler with persistent state"""
    # Store absolute min/max dates separately
    if 'absolute_dates' not in st.session_state:
        try:
            min_date = Participant.objects.earliest('created_at').created_at.date()
            max_date = Participant.objects.latest('created_at').created_at.date()
            st.session_state.absolute_dates = (min_date, max_date)
        except Participant.DoesNotExist:
            st.error("No participant data available")
            return

    # Initialize with absolute dates if not set
    if 'date_range' not in st.session_state:
        st.session_state.date_range = [
            st.session_state.absolute_dates[0],
            st.session_state.absolute_dates[1]
        ]

    # Show date picker with absolute boundaries
    new_dates = st.date_input(
        "Select Date Range",
        value=st.session_state.date_range,
        min_value=st.session_state.absolute_dates[0],
        max_value=st.session_state.absolute_dates[1],
        key="global_date_picker"
    )
    
    # Update session state only if valid new range
    if len(new_dates) == 2:
        st.session_state.date_range = new_dates

def show_participant_metrics():
    """Participant metrics component"""
    st.subheader("Participant Metrics")
    
    try:
        participants = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        count = participants.count()
        
        st.metric("Total Participants", count,
                 help="Includes all participants in selected date range")
        
        # Show timeline
        df = pd.DataFrame(
            participants.values('created_at')
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
        )
        if not df.empty:
            st.line_chart(df.set_index('date'))
        else:
            st.warning("No participants in selected date range")
    except Exception as e:
        st.warning(f"Error loading participant data: {str(e)}")

def show_recommendation_metrics():
    """Recommendation rate component"""
    st.subheader("Recommendation Metrics")
    
    try:
        question = Question.objects.get(
            text__icontains="recommend this event to a friend"
        )
        responses = Response.objects.filter(
            question=question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        
        if responses.exists():
            df = pd.DataFrame(
                responses.values('answer', 'created_at')
                .annotate(date=TruncDate('created_at'))
                .values('date', 'answer')
            )
            
            yes_count = df[df['answer'].str.contains("Yes", case=False)].shape[0]
            total = df.shape[0]
            rate = (yes_count / total) * 100 if total > 0 else 0
            
            col1, col2 = st.columns(2)
            col1.metric("Recommendation Rate", f"{rate:.1f}%")
            col2.metric("Total Responses", total)
            
            daily = df.groupby('date').size()
            st.line_chart(daily.rename("Daily Responses"),color='#d4af37')
        else:
            st.warning("No responses in selected date range")
    except Question.DoesNotExist:
        st.error("Recommendation question not found")
    except Exception as e:
        st.warning(f"Error loading recommendation data: {str(e)}")

def show_preferred_event_format():
    """Preferred Event Formats"""
    st.subheader("Preferred Event Formats")
    
    try:
        question = Question.objects.get(
            text__icontains="What type of events do you prefer"
        )
        responses = Response.objects.filter(
            question=question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        
        if responses.exists():
            format_data = responses.values('answer') \
                .annotate(count=Count('id')) \
                .order_by('-count')
            
            cols = st.columns(len(format_data))
            for idx, fmt in enumerate(format_data):
                with cols[idx]:
                    st.metric(label=fmt['answer'], value=fmt['count'])
                    
            labels = [fmt['answer'] for fmt in format_data]
            values = [fmt['count'] for fmt in format_data]     
            colours = ['#1E3A8A', '#C4A747', '#94A3B8']
            plt.figure(figsize=(6, 4))
            plt.bar(labels, values, color=colours[:len(labels)])  
            plt.xlabel("Event Type")
            plt.ylabel("Count")
            #plt.title("Preferred Event Formats")
            plt.xticks(rotation=45)  # Improves readability for longer labels
            st.pyplot(plt)  # Proper Streamlit display
                    #st.bar_chart(label=fmt['answer'], value=fmt['count'],color=colours)
        else:
            st.info("No event preference data in selected date range")
    except Question.DoesNotExist:
        st.error("Event format question not found")
    except Exception as e:
        st.warning(f"Error loading format data: {str(e)}")

age_ranges = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-89", "90+"]

# Function to calculate midpoint
def calculate_midpoint(age_range):
    """Convert age range (e.g., '18-24') to midpoint value."""
    if "+" in age_range:  # Handle '90+'
        return 95  # Assume 95 for 90+
    else:
        lower, upper = map(int, age_range.split("-"))
        return (lower + upper) / 2

def show_age_data():
    """Age Distribution"""
    #st.subheader("Age Distribution Metrics")
    
    try:
        participants = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        
        count = participants.count()
        
        if count > 0:  
            df = pd.DataFrame(
                participants.annotate(date=TruncDate('created_at'))
                .annotate(count=Count('id'))
                .values('date', 'age', 'count')
            )

            if not df.empty:  
                fig = px.bar(df, x='age', y='count', 
                             title="Age Group Distribution",
                             category_orders={"age": age_ranges})
                st.plotly_chart(fig, use_container_width=True)

                colours = ["brown", "red", "black", "green", "gold", "blue", "gray", "yellow", "white"]

                # Ensure df is correctly formatted
                fig = px.pie(df, names="age", values="count", 
                             title="AGD Pie Chart",
                             color_discrete_sequence=colours[:len(df)])  
                
                # Reduce the size of the pie chart
                fig.update_layout(
                    width=400,  
                    height=400  
                )
                #st.plotly_chart(fig, use_container_width=True)

                st.subheader("Age Overview")
                
                # Convert age ranges to midpoints
                df['age_midpoint'] = df['age'].apply(calculate_midpoint)

                # Debugging output
                #st.write("Debugging Age Midpoints:", df[['age', 'age_midpoint']])

                # Drop NaN values before calculating statistics
                df_clean = df.dropna(subset=['age_midpoint'])

                if not df_clean.empty:
                    avg_age = df_clean['age_midpoint'].mean()
                    max_age = df_clean['age_midpoint'].max()
                    min_age = df_clean['age_midpoint'].min()
                else:
                    avg_age, max_age, min_age = None, None, None

                # Nested horizontal layout for age metrics


                # Nested horizontal layout for age metrics
                age_col1, age_col2, age_col3 = st.columns(3)
                age_col1.metric("Min. Age", f"{min_age:.1f} Yrs" if min_age is not None else "N/A")
                age_col2.metric("Avg. Age", f"{avg_age:.1f} Yrs" if avg_age is not None else "N/A")
                age_col3.metric("Max. Age", f"{max_age:.1f} Yrs" if max_age is not None else "N/A")
        
        else:
            st.warning("No responses in selected date range")

    except Participant.DoesNotExist:
        st.error("Participants not found")
    except Exception as e:
        st.warning(f"Error loading age data: {str(e)}")


def show_demographic_breakdown():
    '''Gender-Ethnicity Sunburst'''
    try:
        participants = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        if participants.exists():  
            df = pd.DataFrame(
                participants.annotate(date=TruncDate('created_at'))
                .values('gender', 'ethnicity')
            )

            # Group by gender and ethnicity to count occurrences
            df = df.groupby(['gender', 'ethnicity']).size().reset_index(name='count')

            if not df.empty:
                fig = px.sunburst(df, path=['gender', 'ethnicity'], 
                                  values='count', title="Demographic Breakdown")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No responses in selected date range")

    except Participant.DoesNotExist:
        st.error("Participants not found")
    except Exception as e:
        st.warning(f"Error loading demographic breakdown: {str(e)}")

def show_gender_data():
    """Gender Distribution"""
    try:
        participants = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        if participants.exists():
            # Create DataFrame with gender counts
            df = pd.DataFrame(
                participants.annotate(date=TruncDate('created_at'))
                .values('gender')
            )

            # Group by gender and count occurrences
            df = df.groupby(['gender']).size().reset_index(name='count')

            if not df.empty:
                # Display gender metrics
                male_count = df[df['gender'] == 'M']['count'].sum() if 'M' in df['gender'].values else 0
                female_count = df[df['gender'] == 'F']['count'].sum() if 'F' in df['gender'].values else 0
                unspecified_count = df[df['gender'] == 'NS']['count'].sum() if 'NS' in df['gender'].values else 0
                
                # Bar chart visualization
                colours = ['#1E3A8A', '#C4A747', '#94A3B8']
                fig = px.bar(df, x='gender', y='count', title="Gender Distribution",color='gender', color_discrete_map={'M': colours[0], 'F': colours[1], 'NS': colours[2]})
                st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3 = st.columns(3)                                                                                                     
                col1.metric("Male", male_count)
                col2.metric("Female", female_count)
                col3.metric("Not Specified", unspecified_count)     
        else:
            st.error("No data for the dates you have selected")

    except Exception as e:
        st.error(f"Can't load data for gender: {str(e)}")

def show_completion():
    '''Showing the evaluation Form completition rate.'''
    try:
        sessions=EvaluationSession.objects.filter(
            completed_at__date__gte=st.session_state.date_range[0],
            completed_at__date__lte=st.session_state.date_range[1])
        
        if sessions.exists():
            total_sessions=sessions.count()
            completed_sessions=sessions.filter(completed=True).count()
        
            if total_sessions > 0:
                rate = (completed_sessions / total_sessions) * 100
                st.metric("Form Completion Rate", f"{rate:.1f}%")
            else:
                st.warning("No sessions found in the selected date range.")
        else:
            st.warning("No sessions found in the selected date range.")
    
    except Exception as e:
        st.error(f"Can't load data for Form Completion: {str(e)}")



def show_accessibility_needs():
    """This function shows accessibility needs."""
    try:
        participants = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(
            participants.annotate(date=TruncDate('created_at'))
            .values('accessibility_needs')
        )

        # Group by accessibility needs and count occurrences
        df = df.groupby(['accessibility_needs']).size().reset_index(name='count')

        if not df.empty:
            # Display accessibility needs metrics
            needs = ['Not sure',
                'hard hearing', 'Need Car', 'No', 'Walking Stick', 'Wheelchair', 'assistive_technology',
                'cognitive_or_neurodiversity', 'dietary_accommodations', 'hearing_assistance',
                'mobility_support', 'no_accessibility_needs', 'visual_assistance'
            ]

            # Bar chart visualization
            fig = px.bar(df, x='accessibility_needs', y='count', title="Accessibility Requirements")
            st.plotly_chart(fig, use_container_width=True)
            
            # Create Streamlit columns for metrics
            col1, col2, col3 = st.columns(3)

            for need in needs:
                count = df[df['accessibility_needs'] == need]['count'].sum() if need in df['accessibility_needs'].values else 0
                #if need == "Walking Stick":
                    #col1.metric("Walking Stick", count)
                #elif need == "Wheelchair":
                    #col2.metric("Wheelchair", count)
                if need == "No":
                    col2.metric("No Accessibility Needs", count)
        else:
            st.write("No data for the chosen dates.")   

    except Exception as e:
        st.error(f"Can't load data because: {str(e)}")


def show_marketing_referrals():
    """General Marketing Referrals"""
    try:
        referrals = Participant.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(
            referrals.annotate(date=TruncDate('created_at'))
            .values('referral_source')
        )

        # Group by referral source and count occurrences
        df = df.groupby(['referral_source']).size().reset_index(name='count')

        if not df.empty:
            # Pie chart visualization
            fig = px.pie(df, names='referral_source', values='count',
                         title="Referral Sources Breakdown", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No referrals for the chosen dates.")

    except Exception as e:
        st.error(f"Error loading data for Marketing: {str(e)}")


def show_social_media_question():
    """Social Media Preference"""
    try:
        # Get the relevant question
        social_media_question = Question.objects.filter(text__icontains="If you chose Social Media").first()

        if not social_media_question:
            st.error("Social media question not found.")
            return

        # Filter responses based on the question and date range
        responses = Response.objects.filter(
            question=social_media_question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(
            responses.annotate(date=TruncDate('created_at'))
            .values('response')
        )

        if not df.empty:
            # Group by response and count occurrences
            df = df.groupby(['response']).size().reset_index(name='count')

            # Calculate percentages
            total = df['count'].sum()
            df['Percentage'] = (df['count'] / total * 100).round(1)

            # Create pie chart
            fig = px.pie(df, names='response', values='count',
                         title="Social Media Platform Distribution",
                         hole=0.3)

            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=1.05
                ),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("No social media answers found for chosen dates.")

    except Exception as e:
        st.error(f"Error loading data for Social Media: {str(e)}")

def show_social_media_question():
    """Social Media Preference"""
    try:
        # Get the relevant question
        social_media_question = Question.objects.filter(text__icontains="If you chose Social Media").first()

        if not social_media_question:
            st.error("Social media question not found.")
            return

        # Filter responses based on the question and date range
        responses = Response.objects.filter(
            question=social_media_question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(
            responses.annotate(date=TruncDate('created_at'))
            .values('answer')
        )

        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['answer']).size().reset_index(name='count')

            # Calculate percentages
            total = df['count'].sum()
            df['Percentage'] = (df['count'] / total * 100).round(1)

            # Create pie chart
            fig = px.pie(df, names='answer', values='count',
                         title="Social Media Platform Distribution",
                         hole=0.3)

            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=1.05
                ),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("No social media answers found for chosen dates.")

    except Exception as e:
        st.error(f"Error loading data for Social Media: {str(e)}")

def show_sentiments():
    """Sentiment Analysis"""
    try:
        # Get the relevant question
        #sentiment_question = Question.objects.filter(id=15).first()
        
        sentiment_question_1 = Question.objects.filter(text__icontains="How has Windrush Foundation influenced your understanding of heritage?").first()
        sentiment_question_2 = Question.objects.filter(text__icontains="What was the most valuable part of the event?").first()
        sentiment_question_3 = Question.objects.filter(text__icontains="What could we improve?").first()
        sentiment_question_4 = Question.objects.filter(text__icontains="Any further comment on the overall event will be greatly appreciated.").first()
        sentiment_question_all=[sentiment_question_1,sentiment_question_2,sentiment_question_3,sentiment_question_4]

        for question in sentiment_question_all:
            sentiment_question=question
        
        if not sentiment_question:
            st.error("Sentiment question not found.")
            return

        # Filter responses based on the question and date range
        sentiment_response = Response.objects.filter(
            question=sentiment_question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        # Convert queryset to DataFrame
        df = pd.DataFrame(
            sentiment_response.values('answer')
        )
        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['answer']).size().reset_index(name='count')

            

            st.subheader("Sentiment Analysis")

            # Get analysis results
            #st.dataframe(df)
            sentiment_results = sentiment_analysis(df['answer'])

            # Display in two columns for better layout
            col1, col2 = st.columns([1, 3])

            with col1:
                # Show summary metrics
                st.metric("Positive Responses", f"{sentiment_results.get('positive', 0)}%")
                st.metric("Neutral Responses", f"{sentiment_results.get('neutral', 0)}%")
                st.metric("Negative Responses", f"{sentiment_results.get('negative', 0)}%")

            with col2:
                # Show detailed dataframe
                st.dataframe(pd.DataFrame.from_dict(sentiment_results, orient='index', columns=['Percentage']),
                             use_container_width=True)

                # Optional: Add visualization
                fig = px.pie(names=list(sentiment_results.keys()),
                             values=list(sentiment_results.values()), title="Sentiment Distribution", hole=0.6)

                # Position legend and labels
                fig.update_layout(
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=0.95,
                        xanchor="left",
                        x=0.65
                    ),
                    showlegend=True
                )

                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No text responses available for sentiment analysis.")

    except Exception as e:
        st.error(f"Error loading data for sentiment analysis: {str(e)}")


def get_all_my_data():
    try:
        private = get_private_data()

        if private is None:
            st.error("Access denied: Not authenticated.")
            return

        # Use private['responses'] instead of passing full dictionary
        private_data = Response.objects.filter(
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )
        # Convert queryset to DataFrame
        df = pd.DataFrame(list(private_data.values('question','answer','participant','created_at')))
        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['question','answer','participant','created_at']).size().reset_index(name='count')
            st.write("Private Data")
            st.dataframe(df, width=1200)  # Adjust width dynamically

        else:
            st.error("No private data available for chosen dates.")       

    except Exception as e:
        st.error(f"Sorry, can't load private data: {str(e)}")


def show_Presentation_Format():
    """Shows the distribution of preferred event formats."""
    try:
        # Fetch the relevant question
        event_format = Question.objects.filter(text__icontains="What events interest you?").first()

        if not event_format:
            st.error("Question not found.")
            return

        # Fetch responses to the question
        event_format_counts = Response.objects.filter(
            question=event_format,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(list(event_format_counts.values('answer', 'created_at')))

        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['answer']).size().reset_index(name='count')

            # Calculate percentages
            total = df['count'].sum()
            df['percentage'] = (df['count'] / total * 100).round(1)

            # Display message if no data found
            if total == 0:
                st.error("No Event format data for selected dates.")
                return

            # Create pie chart
            fig = px.pie(df, names='answer', values='count',
                         title="Event Format Distribution", hole=0.3)

            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=0.65
                ),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)

        else:
            st.error("No Event format data for selected dates.")

    except Exception as e:
        st.error(f"Sorry, can't load event format data: {str(e)}")


def show_windrush_loyalty():
    """Shows how long supporters have been following Windrush Foundation."""
    try:
        # Fetch the relevant question
        loyalty_question = Question.objects.filter(text__icontains="How long have you been following Windrush Foundation?").first()

        if not loyalty_question:
            st.error("Question not found.")
            return
            
        # Fetch responses to the question
        loyalty_answer = Response.objects.filter(
            question=loyalty_question,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(list(loyalty_answer.values('answer', 'created_at')))

        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['answer']).size().reset_index(name="count")

            # Rename columns for clarity
            df = df.rename(columns={'answer': 'Windrush Foundation Loyalty Levels'})

            # Calculate percentages
            total = df['count'].sum()
            df['percentage'] = (df['count'] / total * 100).round(1)

            st.write("How long supporters have been following Windrush Foundation")

            # Create pie chart
            fig = px.pie(df,
                         names='Windrush Foundation Loyalty Levels',
                         values='count',
                         title="Windrush Foundation Loyalty Levels Distribution",
                         hole=0.3)

            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=0.65
                ),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)

        else:
            st.write("No responses yet for this question.")

    except Exception as e:
        st.error(f"Sorry, can't load Windrush loyalty data: {str(e)}")


def show_preferred_session():
    """Shows how long supporters have been following Windrush Foundation."""
    try:
        # Fetch the relevant question
        preferred_session = Question.objects.filter(text__icontains="Which sessions did you find most valuable?").first()

        if not preferred_session:
            st.error("Question not found.")
            return
            
        # Fetch responses to the question
        preferred_session_answer = Response.objects.filter(
            question=preferred_session,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1])
        # Convert queryset to DataFrame
        df = pd.DataFrame(list(preferred_session_answer.values('answer', 'created_at')))

        if not df.empty:
            df = df.groupby(['answer']).size().reset_index(name="count")
            df = df.rename(columns={'answer': 'Preferred Session Format'})
            # Calculate percentages
            total = df['count'].sum()
            df['Percentage'] = (df['count'] / total * 100).round(1)
            st.write("Supporters preferred session format")
            # Create pie chart
            fig = px.pie(df,names='Preferred Session Format',
                         values='count',
                         title="Preferred Session Format Distribution",
                         hole=0.3)
            
            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=0.65),
                    showlegend=True)
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)
        else:
            st.write("No responses yet for this question.")

    except Exception as e:
        st.error(f"Sorry, can't load Windrush loyalty data: {str(e)}")

def show_speaker_rating():
    """Shows ratings for the keynote speaker."""
    try:
        # Fetch the relevant question
        speaker_rating = Question.objects.filter(text__icontains="What did you think of the keynote speaker?").first()

        if not speaker_rating:
            st.error("Question not found.")
            return

        # Fetch responses to the question
        speaker_rating_answer = Response.objects.filter(
            question=speaker_rating,
            created_at__date__gte=st.session_state.date_range[0],
            created_at__date__lte=st.session_state.date_range[1]
        )

        # Convert queryset to DataFrame
        df = pd.DataFrame(list(speaker_rating_answer.values('answer', 'created_at')))

        if not df.empty:
            # Group by answer and count occurrences
            df = df.groupby(['answer']).size().reset_index(name='count')

            # Rename columns for clarity
            df = df.rename(columns={'answer': 'Speaker Rating'})

            # Calculate percentages
            total = df['count'].sum()
            df['percentage'] = (df['count'] / total * 100).round(1)

            # Create pie chart
            fig = px.pie(df,
                         names='Speaker Rating',
                         values='count',
                         title="Speaker Rating Distribution",
                         hole=0.3)

            # Position legend and labels
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.95,
                    xanchor="left",
                    x=0.65
                ),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)

        else:
            st.write("No responses yet for this question.")

    except Exception as e:
        st.error(f"Sorry, can't load speaker rating data: {str(e)}")


def show_private_insights(_private_data):
    """Admin analytics dashboard"""
    st.header("Administrator Dashboard")
    
    # Persistent date picker at top
    handle_dates()
    
    with st.expander("Community Engagement Metrics", expanded=True):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            show_participant_metrics()
        
        with col2:
            show_recommendation_metrics()

            # In the Community Engagement Metrics expander
        with col3:
            show_preferred_event_format()
          

    # Demographic Analysis
    with st.expander("Demographic Insights", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        # Age Distribution
        with col1:
            show_age_data()
        
        # Gender-Ethnicity Sunburst
        with col2:
            show_demographic_breakdown()

        with col3:
            #st.subheader("Gender Distribution")
            show_gender_data()

    # Geographic Analysis
    with st.expander("Visitor Origins Analysis", expanded=True):
        tab1, tab2 = st.tabs(["Heatmap", "Demographic Overlay"])
        
        # Heatmap Tab
        with tab1:
            geo_df = get_geospatial_data()
            if not geo_df.empty:
                fig = px.density_mapbox(
                    geo_df, lat='lat', lon='lon', z='count',
                    radius=20, zoom=5, mapbox_style="carto-positron",
                    title="Participant Density by Location"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No geographic data available")
        
        # In the Demographic Overlay section
    with tab2:
        if 'geo_df' in locals() and not geo_df.empty:
            # Get demographic data with count
            demo_geo_data = Participant.objects.values('postcode', 'age', 'gender', 'ethnicity').annotate(demographic_count=Count('id'))  # Changed alias
        
            # Merge with geographic data
            merged_df = pd.merge(pd.DataFrame(list(demo_geo_data)),
                                 geo_df.rename(columns={'count': 'location_count'}),  # Rename geo count
                                 on='postcode'
                                 )
        
            # Create visualization with correct column names
            if not merged_df.empty:
                fig = px.scatter_mapbox(
                    merged_df,
                    lat='lat',
                    lon='lon',
                    color='ethnicity',
                    size='demographic_count',  # Use correct column name
                    hover_data=['age', 'gender', 'location_count'],
                    title="Demographic Distribution by Location",
                    mapbox_style="carto-positron"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not merge demographic and location data")
        else:
            st.info("Geographic data required for overlay")

    # Performance Metrics
    with st.expander("Performance Analytics", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Completion", "Accessibility", "Marketing"])
        
        # Completion Rates
        with tab1:
            show_completion()
        
        # Accessibility Needs
        with tab2:
            show_accessibility_needs()

        # Referral Sources
        with tab3:
            col1,col2=st.columns(2)
            with col1:
                show_marketing_referrals()
            with col2:
                #with col2:
                show_social_media_question()
     
    
#################################################
    with st.expander("Private Data", expanded=True):
        tab1, tab2 = st.tabs(["Sentiment Analysis","Private Data"])
        with tab1:
            # Perform sentiment analysis
            show_sentiments()
          
        with tab2:
            get_all_my_data()
    
    with st.expander("Other Metrics"):
        tab1, tab2, tab3, tab4 = st.tabs(["Presentation Format","About Windrush Foundation","Preferred Session Format", "Speaker Rating"])
        with tab1:
             show_Presentation_Format()

        with tab2:
            show_windrush_loyalty()
        
        with tab3:
            show_preferred_session()

        with tab4:
            show_speaker_rating()
# Add force refresh button
    if st.button("Refresh All Data"):
        st.session_state.clear()
        st.rerun()


from textblob import TextBlob  # Requires textblob package

def sentiment_analysis(responses):
    analysis = {'positive': 0, 'neutral': 0, 'negative': 0}
    
    for text in responses:
        if isinstance(text, str):  # Handle potential non-string values
            polarity = TextBlob(text).sentiment.polarity
            if polarity > 0.2:
                analysis['positive'] += 1
            elif polarity < -0.2:
                analysis['negative'] += 1
            else:
                analysis['neutral'] += 1
    
    # Convert counts to percentages
    total = sum(analysis.values()) or 1  # Prevent division by zero
    return {k: round((v/total)*100, 1) for k, v in analysis.items()}

# ========================
# MAIN APPLICATION
# ========================

import time
from datetime import datetime
def main():
    st.set_page_config(
        page_title="Windrush Insights",
        layout="wide",
        page_icon="📊"
    )

    # Add this to force session handling via Streamlit Cloud
    st.session_state.disable_embedded_session = True  # 👈 Critical line
   
    # Custom CSS
    # css = """
    # <style>
    # [data-testid="stSidebar"] { background-color: #1E3A8A; }
    # .stButton>button { background-color: #C4A747!important; color: #1E3A8A!important; }
    # [data-testid="stTextInput"] input { color: #1E3A8A!important; background: #F8FAFC!important; }
    # </style>
    # """
    # st.markdown(css, unsafe_allow_html=True)

        # CSS for Styling
    custom_css = """
    <style>
    /* Main sidebar styling */
    [data-testid="stSidebar"] { 
        background-color: #1E3A8A;
    }

    /* Button styling */
    .stButton > button {
        background-color: #C4A747 !important;
        color: #1E3A8A !important;
        border: 2px solid #1E3A8A !important;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #1E3A8A !important;
        color: #C4A747 !important;
        border-color: #C4A747 !important;
    }

    /* Text input styling */
    [data-testid="stTextInput"] input {
        background-color: #F8FAFC !important;
        color: #1E3A8A !important;
        border: 2px solid #1E3A8A !important;
        border-radius: 8px;
        padding: 12px !important;
    }

    [data-testid="stTextInput"] input:focus {
        border-color: #C4A747 !important;
        box-shadow: 0 0 0 2px rgba(30, 58, 138, 0.2);
    }

    /* Placeholder text styling */
    [data-testid="stTextInput"] input::placeholder {
        color: #94A3B8 !important;
        opacity: 1;
    }

    /* Dropdown/select styling */
    [data-testid="stSelectbox"] div {
        border: 2px solid #1E3A8A !important;
        border-radius: 8px !important;
    }

    /* Text area styling */
    [data-testid="stTextArea"] textarea {
        background-color: #F8FAFC !important;
        border: 2px solid #1E3A8A !important;
        border-radius: 8px !important;
        color: #1E3A8A !important;
    }

    /* Target password input label specifically */
    [data-testid="stTextInput"] label {
    color: white !important;
    }

    /* For sidebar context */
    [data-testid="stSidebar"] [data-testid="stTextInput"] label {
    color: white !important;
    }

    /* Target date/time display specifically */
    [data-testid="stSidebar"] .st-emotion-cache-16txtl3 {
    color: white !important;
}

    stAlert {
        color: white !important;
        font-weight: bold !important;
        background-color: white !important;
        border-radius: 5px;
        padding: 10px;
    }
    </style>
    """

    st.markdown(custom_css, unsafe_allow_html=True)

    show_public_components(get_public_data())

    # Authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.sidebar:
            # Sidebar UI components
            col1, col2, col3 = st.columns([1, 2, 6])
            col2.image(logo_path, width=140)
            
            now = datetime.now()
            st.write(f"**Date:** {now.strftime('%d/%m/%Y')}  \n**Time:** {now.strftime('%H:%M:%S')}")
            
            password = st.text_input("Admin Password", type="password")
            if st.button("Login"):
                if password == st.secrets["ADMIN_PW"]:
                    with st.spinner("Loading Admin data...."):
                        #private_data = get_private_data()  # INSIDE spinner
                        time.sleep(1)
                        st.session_state.authenticated = True
                        st.rerun()
                else:
                    st.write("Incorrect credentials, try again.")
            
            col2.image(logo_path_2, width=120)

    # Private dashboard
    if st.session_state.authenticated:
        private_data = get_private_data()
        show_private_insights(private_data)

        # Logout and data export
        col1, col2 = st.columns([6, 1])
        col2.button("🔒 Logout", on_click=lambda: st.session_state.update(authenticated=False))
        
        with st.expander("Raw Data Export"):
            st.download_button(label="Export Full Dataset", data=private_data['responses'].to_csv(), file_name="windrush_data_export.csv")
    st.title("")
    st.title("")
    st.write("Designed by BIS Smart Digital Solutions")
if __name__ == "__main__":
    main()
