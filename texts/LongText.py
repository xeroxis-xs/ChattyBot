import os
from dotenv import load_dotenv

load_dotenv()


TERMS_OF_USE=f"""
##### REMOTE INFORMED CONSENT & TERMS OF USE

**Project Title: Ask Narelle - Your Friendly & Personalized 24-7 Teaching Assistant**     
**NTU-IRB ref no. <IRB-2023-860>**    
*Version: 29 Jan 2024*


**1) Introduction**    
“Ask Narelle”, is an automated chatbot developed on top of Large Language Model which plays a partial role as teaching assistant to answer student queries about the course {os.environ['COURSE_NAME']}. The chatbot was developed mainly for the research study titled “Ask Narelle - Your Friendly & Personalized 24-7 Teaching Assistant”. Before you proceed and use the chatbot, it is important for you to understand the purpose of the research study and what will be expected of you.

**2) Purpose of the Research**    
The aim of this research study is to investigate the feasibility and effectiveness to incorporate Generative AI based chatbot to enhance student learning experience. This study is conducted by Ong Chin Ann, Lecturer from the School of Computer Science & Engineering at Nanyang Technological University.

**3) Procedure, Data Collection**    
The chatbot will be made available and accessible by registered users throughout the semester (except for the period during maintenance or otherwise informed by the chatbot administrator). Only student enrolled in {os.environ['COURSE_NAME']} are allowed to register as a user using the NTU email address. Upon registered, your NTU email address and your name will be recorded in the database. Your conversation and interaction with the chatbot, i.e. chatlog, will be recorded in the database as well.

**4) Data Use and Confidentiality**    
Your identity and personal information will be kept confidential and stored securely. The chatlog stored in the database will be use as part of the chatbot features improvement, analytics (for example, sentiment analysis), and for this research purposes only. The aggregated results and finding from the analysis may be published or presented for academic and scientific purposes only, but your personal information will never be disclosed. Possible outlets of dissemination may be within the project team members and potentially carried forward for future project as background study.

**5) Benefits & Risks**    
Although your participation in this research may not benefit you personally, it will help us understand the effectiveness and practicality to deploy Generative AI based chatbot into the course as study companion/teaching assistant for student and to what extend it would help enhance student learning experience.  There are minimal risks associated when using the application, for example, the response provided by the chatbot might be inaccurate which might cause psychological discomfort or disturbance.  

**6) Voluntary Participation**    
Your participation in this study is completely voluntary, and you have the right to withdraw from the study at any time without any penalty. Your access to the chatbot will be revoked or suspended if you are found (or attempt to) abusing or tempering the chatbot which may causes harm to the chatbot or other users. You may stop using the chatbot if you feel uncomfortable or have loss interest interacting with the chatbot. 

**7) Questions and Concerns**    
If you have questions about this project, you may contact the Principal Investigator, Mr. Ong Chin Ann via email (chinann.ong@ntu.edu.sg) or call 6790 6207.  

This project has been reviewed and approved by NTU-Institutional Review Board. Questions concerning your rights as a participant in this research may be directed to the NTU-IRB at IRB@ntu.edu.sg or call 6592 2495.

**Acknowledgement and Consent**    
Please print a copy of this consent statement for your records, if you so desire.  
"""


CONSENT_ACKNOWLEDGEMENT="*I have read and understood the above consent form. I certify that I am 16 years old or older and, by clicking the next button to register an account and use the chatbot, I indicate my willingness to voluntarily take part in the study.*"

NARELLE_GREETINGS = f"Hi, my name is Narelle. This is the first time I serve as course assistant to help answering your doubts about the course administrative matters such as course structure, schedules, and assessment. \n\nAs I am also new to this course and I will try my very best to answer all your queries accurately with the source of the information *(as of {os.environ['LAST_CONTENT_UPDATE']})*. Where possible try to cross check my answer with the information published at NTU Learn Course Page if in doubts."


PAGE_STYLE="""
<style>
    a{
        color:white;
    }
</style>
"""