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

# Load images

#logo = "dashboard\\images\\Windrush logo clipped1_redrawn BLUEE_v2 3_R1.png"
logo = "dashboard/images/Windrush Logo White_30th Anniversary_2025.png"
logo_path = Image.open(logo) 

#logo2 = "dashboard\\images\\Windrush Foundation 30th Anniversary 2025_R4.png"
logo2 = "dashboard/images/Windrush Foundation 30th Anniversary 2025_R4.png"
logo_path_2 = Image.open(logo2)

# Configure Django environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_dir = os.path.join(project_root, "backend")

#sys.path.extend([project_root, backend_dir])
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

############################
# Force Streamlit to use your public URL
os.environ['STREAMLIT_SERVER_ADDRESS'] = 'https://mikeconel-windrush-evaluation-ap-dashboardmain-dashboard-tiypok.streamlit.app'
os.environ['STREAMLIT_SERVER_PORT'] = '443'  # HTTPS port

# Disable localhost session fallback
st.session_state.update({
    '_host': 'https://mikeconel-windrush-evaluation-ap-dashboardmain-dashboard-tiypok.streamlit.app',
    '_port': 443
})
#################################

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


        # st.markdown("""
        #     <div style='font-weight:bold'>
        #         Your responses will help us improve future events.<br>
        #         Check our website for more events: 
        #         <a href='https://www.windrushfoundation.com/' style='color: #1E3A8A;'>
        #             www.windrushfoundation.com
        #         </a>
        #     </div>""", 
        #     unsafe_allow_html=True
        # )

    # Word Cloud
    with st.container():
        st.markdown("<h5 style='color:blue;font-weight:bold'>Community Feedback Overview</h5>", 
                   unsafe_allow_html=True)
        feedback_data = Response.objects.filter(question__question_type='TX').values_list('answer', flat=True)
        if feedback_data:
            text = ' '.join([d for d in feedback_data if isinstance(d, str)])
            wordcloud = WordCloud(width=1700, height=600).generate(text)
            st.image(wordcloud.to_array(), caption="Most Frequent Feedback Terms")
        else:
            st.info("No text feedback available yet")

def show_private_insights(_private_data):
    """Admin analytics dashboard"""
    st.header("Administrator Dashboard")
    global private_data
    
    # Engagement Metrics
    with st.expander("Community Engagement Metrics", expanded=True):
        col1, col2, col3 = st.columns([1, 4, 2])
        
        # Total Participants
        with col1:
            total = Participant.objects.count()
            st.metric("Total Participants", total)
        
        # Recommendation Rate
        with col2:
            question = Question.objects.filter(text__icontains="recommend this event to a friend").first()
            if question:
                responses = Response.objects.filter(question=question)
                yes_count = responses.filter(answer__icontains="Yes").count()
                total_responses = responses.count()
                
                if total_responses > 0:
                    rate = (yes_count / total_responses) * 100
                    col_a, col_b = st.columns(2)
                    col_a.metric("Would Recommend", f"{rate:.1f}%", 
                               help=f"{yes_count} positive responses")
                    col_b.metric("Would Not Recommend", f"{100-rate:.1f}%",
                               help=f"{total_responses - yes_count} negative responses")
                else:
                    st.warning("No recommendation responses")
            else:
                st.error("Recommendation question not found")
        
        # Event Preferences
        #
        # with col3:

            # In the Community Engagement Metrics expander
        with col3:
            st.write("Preferred Event Formats")
            format_question = Question.objects.filter(text__icontains="What type of events do you prefer").first()
    
            if format_question:
                format_data = Response.objects.filter(question=format_question) \
                    .values('answer') \
                        .annotate(count=Count('id')) \
                            .order_by('-count')
               
                if format_data.exists():
                # Create columns dynamically based on number of responses
                    cols = st.columns(len(format_data))
                    for idx, fmt in enumerate(format_data):
                        with cols[idx]:
                            st.metric(label=fmt['answer'],value=fmt['count'])
                else:
                    st.info("No event preference data")
            else:
                st.error("Event format question not found")

    # Demographic Analysis
    with st.expander("Demographic Insights", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        # Age Distribution
        with col1:
            age_data = Participant.objects.values('age').annotate(count=Count('id'))
            if age_data.exists():
                fig = px.bar(age_data, x='age', y='count', 
                           title="Age Group Distribution",
                           category_orders={"age": [c[0] for c in Participant.AGE_RANGES]})
                st.plotly_chart(fig, use_container_width=True)

                # # === Left Column: Age Metrics ===
#         #with col1:
            st.subheader("Age Overview")
            avg_age_data = Participant.objects.aggregate(avg_age=Avg('age'))
            avg_age = avg_age_data['avg_age']
            
            age_extremes = Participant.objects.aggregate(max_age=Max('age'),min_age=Min('age'))
            max_age = age_extremes['max_age']
            min_age = age_extremes['min_age']
            
            #Will use trhe below when I move over to postgre SQL
            # age_stats = Participant.objects.aggregate(std_dev=StdDev('age'))
            # std_dev = age_stats['std_dev']
            # st.write(std_dev)
            

            # Nested horizontal layout for age metrics
            age_col1, age_col2, age_col3 = st.columns(3)
            age_col1.metric("Min. Age", f"{min_age:.1f} Yrs" if isinstance(min_age, (int, float)) else min_age or "N/A")
            age_col2.metric("Avg. Age", f"{avg_age:.1f}" if isinstance(avg_age, (int, float)) else avg_age or "N/A")
            age_col3.metric("Max. Age", f"{max_age:.1f} Yrs" if isinstance(max_age, (int, float)) else max_age or "N/A")
        
        # Gender-Ethnicity Sunburst
        with col2:
            demo_data = Participant.objects.values('gender', 'ethnicity').annotate(count=Count('id'))
            if demo_data.exists():
                fig = px.sunburst(demo_data, path=['gender', 'ethnicity'], 
                                values='count', title="Demographic Breakdown")
                st.plotly_chart(fig, use_container_width=True)
        
        # Gender Distribution
        with col3:
            gender_data = Participant.objects.values('gender').annotate(count=Count('id'))
            if gender_data.exists():
                counts = [item['count'] for item in gender_data]
                genders = [item['gender'] for item in gender_data]
                
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.barh(genders, counts, color=['#1E3A8A', '#C4A747', '#94A3B8'])
                ax.set_xlabel('Participants')
                ax.set_title('Gender Distribution')
                st.pyplot(fig)
            
            st.subheader("Gender Distribution")
            gender_data = Participant.objects.values('gender') \
                .annotate(count=Count('id')) \
                    .order_by('-count')
    
            if gender_data.exists():
                # Create mapping from gender codes to labels
                gender_labels = dict(Participant.GENDER_CHOICES)
                counts = {
                gender_labels[item['gender']]: item['count'] 
                for item in gender_data
                }
        
                # Display metrics with proper labels
                col1, col2, col3 = st.columns(3)
                col1.metric("Male", counts.get('Male', 0))
                col2.metric("Female", counts.get('Female', 0))
                col3.metric("Not Specified", counts.get('Not Specified', 0))
            else:
                st.info("No gender data available")

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
            sessions = EvaluationSession.objects.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(completed=True))
            )
            if sessions['total'] > 0:
                rate = (sessions['completed'] / sessions['total']) * 100
                st.metric("Form Completion Rate", f"{rate:.1f}%")
        
        # Accessibility Needs
        with tab2:
            needs = Participant.objects.exclude(accessibility_needs__exact='')\
                     .values('accessibility_needs').annotate(count=Count('id'))
            if needs.exists():
                fig = px.bar(needs, x='accessibility_needs', y='count',
                           title="Accessibility Requirements")
                st.plotly_chart(fig, use_container_width=True)
        
        # Referral Sources
        with tab3:
            col1,col2=st.columns(2)
            with col1:
                referrals = Participant.objects.exclude(referral_source__exact='')
                if referrals.exists():
                    sources = pd.DataFrame(list(
                        referrals.values('referral_source').annotate(count=Count('id'))
                    ))
                    fig = px.pie(sources, names='referral_source', values='count',
                            title="Referral Sources Breakdown", hole=0.3)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                #with col2:
                social_media_question = Question.objects.filter(text__icontains="If you chose Social Media").first()
    
                if social_media_question:
                    #st.subheader("Social Media Platforms Usage")
        
        # Get aggregated data
                    platform_counts = Response.objects.filter(question=social_media_question) \
                        .values('answer') \
                            .annotate(count=Count('id')) \
                                .order_by('answer')
                   
                    cleaned_data=[{'answer':items['answer'].strip('"'),'count':items['count']} for items in platform_counts]
                    # Create DataFrame with proper structure
                    df = pd.DataFrame(cleaned_data) \
                    .rename(columns={'answer': 'Platform', 'count': 'Count'})
                    if not df.empty:
                    # Calculate percentages
                        total = df['Count'].sum()
                        df['Percentage'] = (df['Count'] / total * 100).round(1)
            
                    # Create pie chart
                        fig = px.pie(df, 
                                 names='Platform',
                                 values='Count',
                                 title="Social Media Platform Distribution",
                                 hole=0.3)
            
                    # Position legend and labels
                        fig.update_layout(
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.95,
                            xanchor="left",
                            x=1.05),
                            showlegend=True
                            )
            
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("No responses yet for this question")
                else:
                    st.write("Question not found")
        
        
    
#################################################
    with st.expander("Private Data", expanded=True):
        tab1, tab2 = st.tabs(["Sentiment Analysis","Private Data"])
        with tab1:
            # Perform sentiment analysis
            text_responses = Response.objects.filter(question_id='15').values_list('answer', flat=True)
    
            if text_responses.exists():
                st.subheader("Sentiment Analysis")
            # Get analysis results
                sentiment_results = sentiment_analysis(text_responses)
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
                             values=list(sentiment_results.values()),title="Sentiment Distribution", hole=0.6)
                # Position legend and labels
                fig.update_layout(
                    legend=dict(
                        orientation="v",
                            yanchor="top",
                            y=0.95,
                            xanchor="left",
                            x=0.65),
                            showlegend=True
                            )
            
                st.plotly_chart(fig, use_container_width=True)
        
            else:
                st.warning("No text responses available for sentiment analysis")
        with tab2:
            private_data = get_private_data()
            #st.write(private_data)
            st.write("Private Data", private_data['responses'])
    with st.expander("Other Metrics"):
        tab1, tab2, tab3, tab4 = st.tabs(["Presentation Format","About Windrush Foundation","Preferred Session Format", "Speaker Rating"])
        with tab1:
            event_format = Question.objects.filter(text__icontains="What events interest you?").first()
            if event_format:
        # Get aggregated data
                    event_format_counts = Response.objects.filter(question= event_format) \
                        .values('answer') \
                            .annotate(count=Count('id')) \
                                .order_by('answer')
                   
                    cleaned_data=[{'answer':items['answer'].strip('"'),'count':items['count']} for items in event_format_counts]
                    # Create DataFrame with proper structure
                    df = pd.DataFrame(cleaned_data) \
                    .rename(columns={'answer': 'Event Format', 'count': 'Count'})
                    if not df.empty:
                    # Calculate percentages
                        total = df['Count'].sum()
                        df['Percentage'] = (df['Count'] / total * 100).round(1)
                        # Create pie chart
                        fig = px.pie(df, 
                                 names='Event Format',
                                 values='Count',
                                 title="Event Format Distribution",
                                 hole=0.3)
            
                    # Position legend and labels
                        fig.update_layout(
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.95,
                            xanchor="left",
                            x=0.65),
                            showlegend=True
                            )
            
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(df)
                    else:
                        st.write("No responses yet for this question")
            else:
                st.write("Question not found")

        with tab2:
            wf_loyalty = Question.objects.filter(text__icontains="How long have you been following Windrush Foundation?").first()
            if wf_loyalty:
        # Get aggregated data
                    wf_loyalty_counts = Response.objects.filter(question=wf_loyalty) \
                        .values('answer') \
                            .annotate(count=Count('id')) \
                                .order_by('answer')
                   
                    cleaned_data=[{'answer':items['answer'].strip('"'),'count':items['count']} for items in wf_loyalty_counts]
                    # Create DataFrame with proper structure
                    df = pd.DataFrame(cleaned_data) \
                    .rename(columns={'answer': 'Windrush Foundation Loyalty Levels', 'count': 'Count'})
                    if not df.empty:
                    # Calculate percentages
                        total = df['Count'].sum()
                        df['Percentage'] = (df['Count'] / total * 100).round(1)
                        st.write("How long supporters have been following Windrush Foundation")
                        # Create pie chart
                        fig = px.pie(df, 
                                 names='Windrush Foundation Loyalty Levels',
                                 values='Count',
                                 title="Windrush Foundation Loyalty Levels Distribution",
                                 hole=0.3)
            
                    # Position legend and labels
                        fig.update_layout(
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.95,
                            xanchor="left",
                            x=0.65),
                            showlegend=True
                            )
            
                        st.plotly_chart(fig, use_container_width=True)
                        #st.dataframe(df)
                    else:
                        st.write("No responses yet for this question")
            else:
                st.write("Question not found")
        
        with tab3:
            preferred_session = Question.objects.filter(text__icontains="Which sessions did you find most valuable?").first()
            if preferred_session:
        # Get aggregated data
                    preferred_session_counts = Response.objects.filter(question=preferred_session) \
                        .values('answer') \
                            .annotate(count=Count('id')) \
                                .order_by('answer')
                   
                    cleaned_data=[{'answer':items['answer'].strip('"'),'count':items['count']} for items in preferred_session_counts]
                    # Create DataFrame with proper structure
                    df = pd.DataFrame(cleaned_data) \
                    .rename(columns={'answer': 'Preferred Session Format', 'count': 'Count'})
                    if not df.empty:
                    # Calculate percentages
                        total = df['Count'].sum()
                        df['Percentage'] = (df['Count'] / total * 100).round(1)
                        st.write("Supporters preferred session format")
                        # Create pie chart
                        fig = px.pie(df, 
                                 names='Preferred Session Format',
                                 values='Count',
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
                            showlegend=True
                            )
            
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(df)
                    else:
                        st.write("No responses yet for this question")
            else:
                st.write("Question not found")

        with tab4:
            speaker_rating = Question.objects.filter(text__icontains="What did you think of the keynote speaker?").first()
            if speaker_rating:
        # Get aggregated data
                    speaker_rating_counts = Response.objects.filter(question=speaker_rating) \
                        .values('answer') \
                            .annotate(count=Count('id')) \
                                .order_by('answer')
                   
                    cleaned_data=[{'answer':items['answer'].strip('"'),'count':items['count']} for items in speaker_rating_counts]
                    # Create DataFrame with proper structure
                    df = pd.DataFrame(cleaned_data) \
                    .rename(columns={'answer': 'Speaker Rating', 'count': 'Count'})
                    if not df.empty:
                    # Calculate percentages
                        total = df['Count'].sum()
                        df['Percentage'] = (df['Count'] / total * 100).round(1)
                        # Create pie chart
                        fig = px.pie(df, 
                                 names='Speaker Rating',
                                 values='Count',
                                 title="Speaker Rating Distribution",
                                 hole=0.3)
            
                    # Position legend and labels
                        fig.update_layout(
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.95,
                            xanchor="left",
                            x=0.65),
                            showlegend=True
                            )
            
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(df)
                    else:
                        st.write("No responses yet for this question")
            else:
                st.write("Question not found")
    




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

    # Add these lines to override session handling
    from streamlit.web.server.websocket_headers import _get_websocket_headers
    headers = _get_websocket_headers()
    if headers and "Host" in headers:
        st.write(f"""<meta property="streamlit:host" content="{headers["Host"]}">""", unsafe_allow_html=True)
   
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
    st.write("Designed by BIS Smart Digital Technologies")
if __name__ == "__main__":
    main()


# import streamlit as st
# import time
# from datetime import datetime


# def main():
#     st.set_page_config(
#         page_title="Windrush Insights",
#         layout="wide",
#         page_icon="📊"
#     )

#     #global private_data
#     #global public_data 
#         # Custom CSS
#     # css = """
#     # <style>
#     # [data-testid="stSidebar"] { background-color: #1E3A8A; }
#     # .stButton>button { background-color: #C4A747!important; color: #1E3A8A!important; }
#     # [data-testid="stTextInput"] input { color: #1E3A8A!important; background: #F8FAFC!important; }
#     # </style>
#     # """
#     # st.markdown(css, unsafe_allow_html=True)
        
#     # CSS for Styling
#     custom_css = """
#     <style>
#     /* Main sidebar styling */
#     [data-testid="stSidebar"] { 
#         background-color: #1E3A8A;
#     }

#     /* Button styling */
#     .stButton > button {
#         background-color: #C4A747 !important;
#         color: #1E3A8A !important;
#         border: 2px solid #1E3A8A !important;
#         font-weight: bold;
#         transition: all 0.3s ease;
#     }

#     .stButton > button:hover {
#         background-color: #1E3A8A !important;
#         color: #C4A747 !important;
#         border-color: #C4A747 !important;
#     }

#     /* Text input styling */
#     [data-testid="stTextInput"] input {
#         background-color: #F8FAFC !important;
#         color: #1E3A8A !important;
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px;
#         padding: 12px !important;
#     }

#     [data-testid="stTextInput"] input:focus {
#         border-color: #C4A747 !important;
#         box-shadow: 0 0 0 2px rgba(30, 58, 138, 0.2);
#     }

#     /* Placeholder text styling */
#     [data-testid="stTextInput"] input::placeholder {
#         color: #94A3B8 !important;
#         opacity: 1;
#     }

#     /* Dropdown/select styling */
#     [data-testid="stSelectbox"] div {
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px !important;
#     }

#     /* Text area styling */
#     [data-testid="stTextArea"] textarea {
#         background-color: #F8FAFC !important;
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px !important;
#         color: #1E3A8A !important;
#     }

#     /* Target password input label specifically */
#     [data-testid="stTextInput"] label {
#     color: white !important;
#     }

#     /* For sidebar context */
#     [data-testid="stSidebar"] [data-testid="stTextInput"] label {
#     color: white !important;
#     }

#     /* Target date/time display specifically */
#     [data-testid="stSidebar"] .st-emotion-cache-16txtl3 {
#     color: white !important;
# }

#     </style>
#     """
#     st.markdown(custom_css , unsafe_allow_html=True)

#     public_data = get_public_data()  # Load actual data
#     show_public_components(public_data)

#     # Authentication logic
#     if 'authenticated' not in st.session_state:
#         st.session_state.authenticated = False

#     if not st.session_state.authenticated:
#         with st.sidebar:
#             # Sidebar components
#             col1, col2, col3 = st.columns([1, 2, 6])
#             col2.image(logo_path, width=140)
            
#             now = datetime.now()
#             st.write(f"**Date:** {now.strftime('%d/%m/%Y')}  \n**Time:** {now.strftime('%H:%M:%S')}")
            
#             password = st.text_input("Admin Password", type="password")

#             if st.button("Login"):
#                 if password == st.secrets["ADMIN_PW"]:
#                     with st.spinner(""):
#                         st.markdown("""
#                         <div class="spinner"></div>
#                         <p style='text-align: center;'>Please wait loading admin data...</p>
#                         """, unsafe_allow_html=True)
#                         private_data = get_private_data()  # INSIDE spinner
#                         time.sleep(1)
#                         st.session_state.authenticated = True
#                         if st.session_state.authenticated:
#                             show_private_insights(private_data)
#                         st.rerun()
#                         if st.session_state.authenticated:
#                             show_private_insights(private_data)
#                 else:
#                     st.error("Incorrect credentials")

#     # Private dashboard
#     #if st.session_state.authenticated:
#      #   show_private_insights(private_data)  # Now uses pre-loaded data

#         #Logout and data export
#         col1, col2 = st.columns([6, 1])
#         col2.button("🔒 Logout", on_click=lambda: st.session_state.update(authenticated=False))
        
#         with st.expander("Raw Data Export"):
#             st.download_button(
#                 label="Export Full Dataset",
#                 data=private_data['responses'].to_csv(),
#                 file_name="windrush_data_export.csv"
#             )

# if __name__ == "__main__":
#     main()


#THIS BELOW IS WORKING FINE AS OF 08/04/2025

# from django.db.models import Count, Q, F, Avg, Max, Min , StdDev
# import streamlit as st
# import sqlite3
# import pandas as pd
# from textblob import TextBlob
# import plotly.express as px
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter
# import matplotlib.pyplot as plt
# from wordcloud import WordCloud
# import os
# import sys
# import requests
# from django.db import connection
# import django
# import json
# from django.db.models import FloatField
# from django.db.models.functions import Cast
# from PIL import Image
# import datetime
# from datetime import datetime



# logo ="dashboard\\images\\Windrush logo clipped1_redrawn BLUEE_v2 3.jpg"
# logo_path = Image.open(logo) 
# logo2 ="dashboard\\images\\Windrush Foundation 30th Anniversary 2025_R4.png"
# logo_path_2 = Image.open(logo2) 

# # Get absolute paths
# current_dir = os.path.dirname(os.path.abspath(__file__))          # /dashboard
# project_root = os.path.dirname(current_dir)                      # /windrush
# backend_dir = os.path.join(project_root, "backend")              # /windrush/backend

# # Add to Python path
# sys.path.extend([
#     project_root,    # For Django project recognition
#     backend_dir      # For app module resolution
# ])

# # Django configuration
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
# django.setup()

# # Now import models
# #from evaluations.models import Participant, Response, Question
# from evaluations.models import Participant, Response, Question, EvaluationSession 

# # dashboard/main_dashboard.py

# @st.cache_data(ttl=3600)
# def get_public_data():
#     """Aggregate data without personal identifiers"""
#     return {
#         'participants': Participant.objects.values('gender', 'ethnicity', 'age'),
#         'responses': Response.objects.values('question__text', 'answer'),
#         'sessions': EvaluationSession.objects.filter(completed=True)
#     }

# @st.cache_data(ttl=300)
# def get_private_data():
#     """Sensitive data only for authenticated users"""
#     if st.session_state.get('authenticated'):
#         return {
#             'participants': pd.DataFrame(list(Participant.objects.all().values())),
#             'responses': pd.DataFrame(list(Response.objects.all().values())),
#             'sessions': EvaluationSession.objects.all()
#         }
#     return None




# def show_public_components(data):
#     """Components visible to all users"""
#     # Success message and PDF download
#     session_key = st.experimental_get_query_params().get('session_key', [None])[0]
#     if session_key:
#         st.title(':blue[Thank You for Participating!]')
#         st.markdown(f"<div style='font-weight:bold'>in the survey for today's event. Your responses will help us improve future events.</div>",unsafe_allow_html=True)
#         st.markdown(f"<p style='font-weight:bold'>For more Windrush Foundation events, check out our website:<a href='https://www.windrushfoundation.com/'><h5>www.windrushfoundation.com</h></a></p>",unsafe_allow_html=True)
#         #st.markdown(
#         #    f'[Download PDF of your anwsers](http://localhost:8000/download-pdf/{session_key})',
#         #    unsafe_allow_html=True)
    
#     # Feedback Analysis (Word Cloud)
#     with st.container():
#         st.markdown(f"<h5 style='color:blue;font-weight:bold'>Word Cloud Community Feedback Overview</h5>", unsafe_allow_html=True)
#         feedback_data = Response.objects.filter(question__question_type='TX').values_list('answer', flat=True)
#         if feedback_data:
#             text = ' '.join([d for d in feedback_data if isinstance(d, str)])
#             wordcloud = WordCloud(width=800, height=400).generate(text)
#             st.image(wordcloud.to_array(), caption="Common Feedback Themes")
#         else:
#             st.info("No text feedback available yet")

# @st.cache_data(show_spinner=False)
# def show_private_insights(_private_data):
#     """Admin-only strategic insights"""
#     st.header("Administrator Dashboard")
    
#     # Engagement Metrics
#     with st.expander("Community Engagement Metrics", expanded=True):
#         col1, col2, col3 = st.columns([1,4,2])
#         with col1:
#             total_participants = Participant.objects.count()
#             st.metric("Total Participants", total_participants)
            
#         with col2:
#             recommendation_question = Question.objects.filter(text__icontains="Would you recommend this event to a friend").first()
#             if recommendation_question:
#                 # Count valid responses
#                 yes_count = Response.objects.filter(question=recommendation_question,answer__icontains="Yes" ).count()
#                 total_responses = Response.objects.filter(question=recommendation_question).count()
                
#                 co1_a, col_b = st.columns(2)
#                 if total_responses > 0:
#                     recommend_rate = (yes_count / total_responses) * 100
#                     with co1_a:
#                         st.metric("Would Recommend Events to Friends", f"{recommend_rate:.1f}%",help=f"{yes_count} of {total_responses} participants said Yes")
#                     with col_b:
#                         st.metric("Would Not Recommend Events to Friends", f"{100-recommend_rate:.1f}%",help=f"{total_responses-yes_count} of {total_responses} participants said No")
#                 else:
#                     st.warning("No responses recorded for this question")
#             else:
#                 st.error("Recommendation question not found in database")

#             # if recommendation_question:
#             #     recommendations = Response.objects.filter(question_id='10'
#             #      ).annotate(numeric_answer=Cast('answer', FloatField())).aggregate(('numeric_answer'))
#             #     st.write(recommendations)
                


#                 # recommendations = Response.objects.filter(question=recommendation_question
#                 # ).annotate(numeric_answer=Cast('answer', FloatField())).aggregate(recommend_rate=Avg('numeric_answer'))
#                 # st.write(recommendations)
#                 # st.metric("Recommendation Rate", 
#                 #         f"{recommendations['recommend_rate']*100:.1f}%" 
#                 #         if recommendations['recommend_rate'] else "N/A")
                
#         with col3:
#             st.write("preferred event format")
#             format_question = Question.objects.filter(text__icontains="What type of events do you prefer").first()
#             #st.write(format_question)
#             if format_question:
#                 format_data = Response.objects.filter(
#                     question_id='21'
#                 ).values('answer').annotate(count=Count('id'))
#                 #st.write(format_data)
#                 col_a,col_b,col_c = st.columns(3)
#                 with col_a:
#                     st.metric(format_data[0].get('answer'),format_data[0].get('count'))
#                 with col_b:
#                     st.metric(format_data[1].get('answer'),format_data[1].get('count'))
#                 with col_c:
#                     st.metric(format_data[1].get('answer'),format_data[1].get('count'))
#                 #format_data=format_data[1].get('"Offline"')
#                 #st.metric(format_data,"Preferred Event Formats")
#                 # fig = px.pie(format_data, names='answer', values='count', 
#                 #            title="Preferred Event Formats")
#                 #st.plotly_chart(fig, use_container_width=True)
#                 #question=format_question 

#     # Demographic Insights
#     with st.expander("Demographic Analysis", expanded=True):
#         col1, col2,col3 = st.columns(3)
#         with col1:
#             # For age distribution chart
#             age_data = Participant.objects.values('age').annotate(count=Count('id'))
#             if age_data.exists():
#                 fig = px.bar(
#                 age_data, 
#                 x='age', 
#                 y='count',
#                 title="Age Group Distribution",
#                 category_orders={"age": [choice[0] for choice in Participant.AGE_RANGES]}
#                 )
#                 st.plotly_chart(fig)
#             # age_data = Participant.objects.values('age').annotate(count=Count('id'))
#             # if age_data:
#             #     fig = px.histogram(age_data, x='age', y='count', 
#             #                      title="Age Distribution")
#             #     st.plotly_chart(fig, use_container_width=True)
       
#         with col2:
#             demo_data = Participant.objects.values('gender', 'ethnicity').annotate(count=Count('id'))
#             if demo_data.exists():
#                 fig = px.sunburst(demo_data, path=['gender', 'ethnicity'], 
#                                 values='count', title="Demographic Breakdown")
#                 st.plotly_chart(fig, use_container_width=True)
#         with col3:
#             #st.markdown("**Gender Distribution**")
#             # Get gender counts from database
#             gender_data = Participant.objects.values('gender').annotate(count=Count('id'))
#             if gender_data.exists():
#                 fig, ax = plt.subplots(figsize=(6, 5))  # Slightly taller height
#                 # Extract labels and counts
#                 genders = [item['gender'] for item in gender_data]
#                 counts = [item['count'] for item in gender_data]#
#                 st.write("Counts",counts[2])
#             # Create plot
#                 fig, ax = plt.subplots()
#                 ax.barh(genders, counts, color=['#1E3A8A', '#C4A747', '#94A3B8'])  # Horizontal bar chart
#             # Formatting
#                 plt.subplots_adjust(top=0.55)  # Reduced from default 0.9
#                 ax.set_xlabel('Number of Participants',size=15)
#                 ax.set_ylabel('Gender',size=15)
#                 ax.set_title('Participant Gender Distribution', size=20, y=1.35)
#                 plt.tight_layout()
#                 #st.header(" ")
#                 st.pyplot(fig)
#             else:
#                 st.info("No gender data available")
        
#         col1, col2, col3 = st.columns(3)

# # === Left Column: Age Metrics ===
#         with col1:
#             st.subheader("Age Overview")
#             avg_age_data = Participant.objects.aggregate(avg_age=Avg('age'))
#             avg_age = avg_age_data['avg_age']
            
#             age_extremes = Participant.objects.aggregate(max_age=Max('age'),min_age=Min('age'))
#             max_age = age_extremes['max_age']
#             min_age = age_extremes['min_age']
            
#             #Will use trhe below when I move over to postgre SQL
#             # age_stats = Participant.objects.aggregate(std_dev=StdDev('age'))
#             # std_dev = age_stats['std_dev']
#             # st.write(std_dev)
            

#             # Nested horizontal layout for age metrics
#             age_col1, age_col2, age_col3 = st.columns(3)
#             age_col1.metric("Min. Age", f"{min_age:.1f} Yrs" if isinstance(min_age, (int, float)) else min_age or "N/A")
#             age_col2.metric("Avg. Age", f"{avg_age:.1f}" if isinstance(avg_age, (int, float)) else avg_age or "N/A")
#             age_col3.metric("Max. Age", f"{max_age:.1f} Yrs" if isinstance(max_age, (int, float)) else max_age or "N/A")
            
#         # === Right Column: Gender Count Metrics ===
#         with col3:
#             st.subheader("Gender Distribution")
#             if counts is not None and len(counts) >= 3:
#                 g_col1, g_col2, g_col3 = st.columns(3)
#                 g_col1.metric("Males", counts[1])
#                 g_col2.metric("Females", counts[0])
#                 g_col3.metric("Other/NA", counts[2])


#     with st.expander("Visitor Origins Analysis", expanded=True):
#         tab1, tab2 = st.tabs(["Geospatial Heatmap", "Demographic Overlay"])
        
#         with tab1:
#             st.subheader("Visitor Travel Origins Heatmap")
            
#             # Get postcode data with rate limiting
#             postcodes = Participant.objects.exclude(postcode__exact='').values_list('postcode', flat=True)
            
#             if postcodes:
#                 # Geocode postcodes
#                 geolocator = Nominatim(user_agent="windrush_geo")
#                 geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
                
#                 locations = []
#                 for postcode in postcodes:
#                     try:
#                         location = geocode(postcode)
#                         if location:
#                             locations.append({
#                                 "postcode": postcode,
#                                 "lat": location.latitude,
#                                 "lon": location.longitude
#                             })
#                     except:
#                         continue
                
#                 if locations:
#                     # Create density map
#                     df = pd.DataFrame(locations)
#                     fig = px.density_mapbox(
#                         df,
#                         lat='lat',
#                         lon='lon',
#                         radius=10,
#                         zoom=5,
#                         mapbox_style="stamen-terrain",
#                         title="Geographic Distribution of Visitor Origins",
#                         height=600
#                     )
#                     fig.update_layout(
#                         mapbox_style="carto-positron",
#                         mapbox_zoom=5,
#                         mapbox_center={"lat": 54.00366, "lon": -2.547855}
#                     )
#                     st.plotly_chart(fig, use_container_width=True)
#                 else:
#                     st.warning("Could not geocode postcode data")
#             else:
#                 st.info("No postcode data available in responses")

#         with tab2:
#             st.subheader("Demographic Overlay Analysis")
#             # Add demographic overlay visualizations here


#     with st.expander("Performance Metrics", expanded=True):
#         tab1, tab2, tab3 = st.tabs(["Drop-off Rates", "Accessibility", "Marketing"])
        
#         with tab1:
#             total_sessions = EvaluationSession.objects.count()
#             completed_sessions = EvaluationSession.objects.filter(completed=True).count()
#             dropoff_rate = ((total_sessions - completed_sessions) / total_sessions * 100 
#                          if total_sessions else 0)
#             st.metric("Form Drop-off Rate", f"{dropoff_rate:.1f}%")

#         with tab2:
#             accessibility_data = Participant.objects.values(
#                 'accessibility_needs'
#             ).annotate(count=Count('id'))
#             if accessibility_data.exists():
#                 fig = px.bar(accessibility_data, x='accessibility_needs', y='count',
#                            title="Accessibility Requirements")
#                 st.plotly_chart(fig, use_container_width=True)

#         with tab3:
#             # In your Streamlit dashboard code (main_dashboard.py)

#             st.subheader("Participant Referral Sources")
    
#     # Get all referral sources with case-insensitive cleaning
#             referrals = Participant.objects.exclude(referral_source__exact='').values_list('referral_source', flat=True)
    
#             if referrals.exists():
#         # Debug: Show unique referral sources
#                 #st.write("Found referral sources:", set(referrals))
        
#         # Normalize and categorize
#                 referral_map = {'social': ['instagram', 'facebook', 'twitter', 'social'],
#                                 'word of mouth': ['friend', 'family', 'word', 'colleague'],
#                                 'email': ['email', 'newsletter'],
#                                 'website': ['website', 'web', 'online'],
#                                 'event': ['event', 'festival', 'exhibition']}
        
#                 categorized = {'Other': 0}
#                 for source in referrals:
#                     source_lower = str(source).lower()
#                     matched = False
#                     for category, keywords in referral_map.items():
#                         if any(keyword in source_lower for keyword in keywords):
#                             categorized[category] = categorized.get(category, 0) + 1
#                             matched = True
#                             break
#                     if not matched:
#                         categorized['Other'] += 1
                
#         # Create visualization
#                 fig = px.pie(names=list(categorized.keys()),values=list(categorized.values()),title="Referral Source Breakdown",hole=0.3)
#                 st.plotly_chart(fig, use_container_width=True)
        
#             else:
#                 st.info("No referral sources recorded in participant responses")
        
#     with st.expander("Private Data", expanded=True):
#         tab1, tab2 = st.tabs(["Private Data", "Sentiment Analysis"])
#         with tab1:
#             private_data = get_private_data()
#             st.write("Private Data", private_data['responses'])
#         with tab2:
#             text_responses = Response.objects.filter(question_id='15').values_list('answer', flat=True)
#             tr=sentiment_analysis(text_responses)
#             st.write("Sentiment Analysis",tr)
        

# def sentiment_analysis(text_responses):
#     sentiments = []
#     for text in text_responses:
#         analysis = TextBlob(text)
#         sentiments.append({
#             'text': text,
#             'polarity': analysis.sentiment.polarity,
#             'subjectivity': analysis.sentiment.subjectivity
#         })
#     return pd.DataFrame(sentiments)      


# from datetime import datetime

# def main():
#     st.set_page_config(
#         page_title="Windrush Insights",
#         layout="wide",
#         page_icon="📊"
#     )

#     # CSS for Styling
#     # CSS for Styling
#     custom_css = """
#     <style>
#     /* Main sidebar styling */
#     [data-testid="stSidebar"] { 
#         background-color: #1E3A8A;
#     }

#     /* Button styling */
#     .stButton > button {
#         background-color: #C4A747 !important;
#         color: #1E3A8A !important;
#         border: 2px solid #1E3A8A !important;
#         font-weight: bold;
#         transition: all 0.3s ease;
#     }

#     .stButton > button:hover {
#         background-color: #1E3A8A !important;
#         color: #C4A747 !important;
#         border-color: #C4A747 !important;
#     }

#     /* Text input styling */
#     [data-testid="stTextInput"] input {
#         background-color: #F8FAFC !important;
#         color: #1E3A8A !important;
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px;
#         padding: 12px !important;
#     }

#     [data-testid="stTextInput"] input:focus {
#         border-color: #C4A747 !important;
#         box-shadow: 0 0 0 2px rgba(30, 58, 138, 0.2);
#     }

#     /* Placeholder text styling */
#     [data-testid="stTextInput"] input::placeholder {
#         color: #94A3B8 !important;
#         opacity: 1;
#     }

#     /* Dropdown/select styling */
#     [data-testid="stSelectbox"] div {
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px !important;
#     }

#     /* Text area styling */
#     [data-testid="stTextArea"] textarea {
#         background-color: #F8FAFC !important;
#         border: 2px solid #1E3A8A !important;
#         border-radius: 8px !important;
#         color: #1E3A8A !important;
#     }

#     /* Target password input label specifically */
#     [data-testid="stTextInput"] label {
#     color: white !important;
#     }

#     /* For sidebar context */
#     [data-testid="stSidebar"] [data-testid="stTextInput"] label {
#     color: white !important;
#     }

#     /* Target date/time display specifically */
#     [data-testid="stSidebar"] .st-emotion-cache-16txtl3 {
#     color: white !important;
# }

#     </style>
#     """

#     st.markdown(custom_css, unsafe_allow_html=True)
    
#     # Public components
#     public_data = get_public_data()
#     show_public_components(public_data)

#     # Authentication check
#     if 'authenticated' not in st.session_state:
#         st.session_state.authenticated = False
        
#     if not st.session_state.authenticated:
#         with st.sidebar:
#             col1,col2,col3=st.columns([1,2,6])
#             with col2:
#                 st.image(logo_path,width=140)
            
#             now = datetime.now()
#             xtime = now.strftime("%H:%M:%S")
#             today = datetime.today()
#             xdate=today.strftime("%d/%m/%Y")
            
#             st.write(f"{xdate} || {xtime}")
#             password = st.text_input("Admin Password", type="password")
#             if st.button("Login"):
#                 if password == st.secrets["ADMIN_PW"]:
#                     st.session_state.authenticated = True
#                     st.rerun()
#                 else:
#                     st.error("Incorrect password")
#             col1,col2,col3=st.columns([1,2,6])
#             with col2:
#                 st.image(logo_path_2,width=120)

#     # Private components
   
#     ######################################################
#     #elif  st.session_state.authenticated == False
#     if st.session_state.authenticated:
#         private_data = get_private_data()
#         show_private_insights(private_data)
        

#     # ⬇️ Place logout button visibly (e.g. top right or bottom)
#         col1, col2 = st.columns([6, 1])
#         with col2:
#             if st.button("🔓 Logout", key="logout"):
#                 st.session_state.authenticated = False
#                 st.rerun()

#         # Data Export Section
#         st.divider()
#         with st.expander("Raw Data Export"):
#             st.download_button(
#                 label="Download Full Dataset (CSV)",
#                 data=private_data['responses'].to_csv(),
#                 file_name="windrush_full_data.csv")

#     else:
#         st.info("🔐 Admin authentication required for detailed insights")


# if __name__ == "__main__":
#     main()





