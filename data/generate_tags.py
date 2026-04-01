#!/usr/bin/env python3
"""
Generate semantic tags for all 1,396 n8n nodes.

This script analyzes each node's type, name, description, operations, credentials,
and category to assign intent-based tags. Tags enable zero-token retrieval:
  SELECT * FROM nodes WHERE tags LIKE '%messaging%'

Run once to populate the `tags` column. Deterministic — same input = same output.
"""

import sqlite3
import json
import re
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes.db')

# ─── CORE NODE → TAG MAPPING ────────────────────────────────────────────────
# Explicit mappings for core nodes where automated rules alone aren't sufficient.
# Format: node_type_suffix → [tags]
# The suffix is the part after 'nodes-base.' or 'nodes-langchain.'

EXPLICIT_TAGS = {
    # ── Messaging ──
    'slack': ['messaging', 'team-communication', 'send-message', 'notification', 'channel-management'],
    'slackTrigger': ['messaging', 'team-communication', 'trigger-on-event'],
    'discord': ['messaging', 'team-communication', 'send-message', 'notification'],
    'telegram': ['messaging', 'send-message', 'notification', 'voice-sms'],
    'telegramTrigger': ['messaging', 'trigger-on-event'],
    'whatsApp': ['messaging', 'send-message', 'notification', 'voice-sms'],
    'whatsAppTrigger': ['messaging', 'trigger-on-event'],
    'microsoftTeams': ['messaging', 'team-communication', 'send-message', 'notification'],
    'microsoftTeamsTrigger': ['messaging', 'team-communication', 'trigger-on-event'],
    'googleChat': ['messaging', 'team-communication', 'send-message'],
    'line': ['messaging', 'send-message'],
    'mattermost': ['messaging', 'team-communication', 'send-message'],
    'gotify': ['messaging', 'notification', 'send-message'],
    'pushcut': ['messaging', 'notification'],
    'pushover': ['messaging', 'notification'],

    # ── Email ──
    'gmail': ['email', 'send-email', 'read-data', 'notification', 'messaging'],
    'gmailTrigger': ['email', 'trigger-on-event'],
    'emailSend': ['email', 'send-email', 'notification'],
    'emailReadImap': ['email', 'trigger-on-event', 'read-data'],
    'sendGrid': ['email', 'send-email', 'marketing', 'notification'],
    'mailchimp': ['email', 'marketing', 'send-email', 'notification'],
    'mailchimpTrigger': ['email', 'marketing', 'trigger-on-event'],
    'mailjet': ['email', 'send-email'],
    'mandrill': ['email', 'send-email'],
    'sendInBlue': ['email', 'marketing', 'send-email', 'notification'],
    'sendInBlueTrigger': ['email', 'marketing', 'trigger-on-event'],
    'convertKit': ['email', 'marketing', 'send-email'],
    'convertKitTrigger': ['email', 'marketing', 'trigger-on-event'],
    'awsSes': ['email', 'send-email', 'cloud-infra'],
    'mailerLite': ['email', 'marketing', 'send-email'],
    'mailerLiteTrigger': ['email', 'marketing', 'trigger-on-event'],
    'activeCampaign': ['email', 'marketing', 'crm', 'send-email'],
    'activeCampaignTrigger': ['email', 'marketing', 'trigger-on-event'],
    'lemlist': ['email', 'marketing', 'send-email'],
    'lemlistTrigger': ['email', 'marketing', 'trigger-on-event'],
    'getResponse': ['email', 'marketing', 'send-email'],
    'getResponseTrigger': ['email', 'marketing', 'trigger-on-event'],
    'autopilot': ['email', 'marketing'],
    'autopilotTrigger': ['email', 'marketing', 'trigger-on-event'],
    'microsoftOutlook': ['email', 'send-email', 'read-data', 'notification', 'scheduling'],
    'microsoftOutlookTrigger': ['email', 'trigger-on-event'],

    # ── Social Media ──
    'twitter': ['social-media', 'send-message', 'social-posting', 'read-data'],
    'linkedIn': ['social-media', 'social-posting'],
    'facebookGraphApi': ['social-media', 'social-posting', 'read-data'],
    'facebookTrigger': ['social-media', 'trigger-on-event'],
    'facebookLeadAdsTrigger': ['social-media', 'marketing', 'trigger-on-event', 'crm'],
    'reddit': ['social-media', 'read-data', 'web-scraping', 'content-generation'],
    'medium': ['social-media', 'cms', 'content-generation', 'social-posting'],
    'spotify': ['social-media', 'video-audio', 'read-data'],
    'youTube': ['social-media', 'video-audio', 'read-data', 'content-generation'],

    # ── CRM ──
    'hubspot': ['crm', 'crm-automation', 'lead-enrichment', 'read-data', 'write-data'],
    'hubspotTrigger': ['crm', 'trigger-on-event'],
    'salesforce': ['crm', 'crm-automation', 'lead-enrichment', 'read-data', 'write-data'],
    'salesforceTrigger': ['crm', 'trigger-on-event'],
    'pipedrive': ['crm', 'crm-automation', 'read-data', 'write-data'],
    'pipedriveTrigger': ['crm', 'trigger-on-event'],
    'zohoCrm': ['crm', 'crm-automation', 'read-data', 'write-data'],
    'copper': ['crm', 'crm-automation', 'read-data', 'write-data'],
    'copperTrigger': ['crm', 'trigger-on-event'],
    'freshworksCrm': ['crm', 'crm-automation', 'read-data', 'write-data'],
    'affinity': ['crm', 'read-data', 'write-data'],
    'affinityTrigger': ['crm', 'trigger-on-event'],

    # ── Project Management ──
    'jira': ['project-management', 'read-data', 'write-data', 'update-data'],
    'jiraTrigger': ['project-management', 'trigger-on-event'],
    'linear': ['project-management', 'read-data', 'write-data'],
    'linearTrigger': ['project-management', 'trigger-on-event'],
    'trello': ['project-management', 'read-data', 'write-data'],
    'trelloTrigger': ['project-management', 'trigger-on-event'],
    'asana': ['project-management', 'read-data', 'write-data'],
    'asanaTrigger': ['project-management', 'trigger-on-event'],
    'clickUp': ['project-management', 'read-data', 'write-data'],
    'clickUpTrigger': ['project-management', 'trigger-on-event'],
    'todoist': ['project-management', 'productivity', 'read-data', 'write-data'],
    'googleTasks': ['project-management', 'productivity', 'read-data', 'write-data'],
    'microsoftToDo': ['project-management', 'productivity', 'read-data', 'write-data'],

    # ── Developer Tools ──
    'github': ['developer', 'read-data', 'write-data', 'project-management'],
    'githubTrigger': ['developer', 'trigger-on-event'],
    'gitlab': ['developer', 'read-data', 'write-data', 'project-management'],
    'gitlabTrigger': ['developer', 'trigger-on-event'],
    'bitbucketTrigger': ['developer', 'trigger-on-event'],
    'jenkins': ['developer', 'cloud-infra'],
    'circleCi': ['developer', 'cloud-infra'],
    'travisCi': ['developer', 'cloud-infra'],
    'ssh': ['developer', 'cloud-infra', 'execute-code'],
    'netlify': ['developer', 'cloud-infra', 'cms'],
    'netlifyTrigger': ['developer', 'trigger-on-event'],

    # ── Database ──
    'postgres': ['database', 'read-data', 'write-data', 'update-data', 'delete-data', 'search', 'data-pipeline'],
    'postgresTrigger': ['database', 'trigger-on-event'],
    'mySql': ['database', 'read-data', 'write-data', 'update-data', 'delete-data', 'search', 'data-pipeline'],
    'mongoDb': ['database', 'read-data', 'write-data', 'update-data', 'search', 'data-pipeline'],
    'redis': ['database', 'read-data', 'write-data', 'data-pipeline'],
    'redisTrigger': ['database', 'trigger-on-event'],
    'elasticsearch': ['database', 'search', 'read-data', 'write-data', 'analytics'],
    'snowflake': ['database', 'analytics', 'read-data', 'data-pipeline'],
    'googleBigQuery': ['database', 'analytics', 'read-data', 'data-pipeline'],
    'microsoftSql': ['database', 'read-data', 'write-data', 'data-pipeline'],
    'timescaleDb': ['database', 'read-data', 'write-data', 'data-pipeline'],
    'databricks': ['database', 'analytics', 'ai-llm', 'data-pipeline'],
    'oracleDatabase': ['database', 'read-data', 'write-data', 'data-pipeline'],
    'questDb': ['database', 'read-data', 'write-data'],
    'dataTable': ['database', 'read-data', 'write-data', 'update-data', 'data-sync', 'data-pipeline'],
    'supabase': ['database', 'read-data', 'write-data', 'update-data'],

    # ── Spreadsheet ──
    'googleSheets': ['spreadsheet', 'read-data', 'write-data', 'update-data', 'data-sync'],
    'googleSheetsTrigger': ['spreadsheet', 'trigger-on-event'],
    'microsoftExcel': ['spreadsheet', 'read-data', 'write-data'],
    'airtable': ['spreadsheet', 'database', 'read-data', 'write-data', 'update-data'],
    'airtableTrigger': ['spreadsheet', 'trigger-on-event'],
    'baserow': ['spreadsheet', 'database', 'read-data', 'write-data'],
    'seaTable': ['spreadsheet', 'database', 'read-data', 'write-data'],
    'coda': ['spreadsheet', 'productivity', 'read-data', 'write-data'],
    'notion': ['productivity', 'spreadsheet', 'cms', 'read-data', 'write-data'],
    'notionTrigger': ['productivity', 'trigger-on-event'],

    # ── File Storage ──
    'awsS3': ['file-storage', 'cloud-infra', 'file-upload', 'file-download'],
    's3': ['file-storage', 'cloud-infra', 'file-upload', 'file-download'],
    'googleDrive': ['file-storage', 'file-upload', 'file-download'],
    'googleDriveTrigger': ['file-storage', 'trigger-on-event'],
    'dropbox': ['file-storage', 'file-upload', 'file-download'],
    'microsoftOneDrive': ['file-storage', 'file-upload', 'file-download'],
    'microsoftOneDriveTrigger': ['file-storage', 'trigger-on-event'],
    'googleCloudStorage': ['file-storage', 'cloud-infra', 'file-upload', 'file-download'],
    'azureStorage': ['file-storage', 'cloud-infra', 'file-upload', 'file-download'],
    'ftp': ['file-storage', 'file-upload', 'file-download'],
    'microsoftSharePoint': ['file-storage', 'read-data', 'write-data'],

    # ── Cloud Infrastructure ──
    'awsLambda': ['cloud-infra', 'execute-code'],
    'awsSns': ['cloud-infra', 'queue', 'notification', 'send-message'],
    'awsSnsTrigger': ['cloud-infra', 'queue', 'trigger-on-event'],
    'awsSqs': ['cloud-infra', 'queue'],
    'awsDynamoDb': ['cloud-infra', 'database', 'read-data', 'write-data'],
    'awsComprehend': ['cloud-infra', 'ai-processor', 'analyze-text'],
    'awsTextract': ['cloud-infra', 'document-processing', 'file-process'],
    'awsElb': ['cloud-infra'],
    'awsIam': ['cloud-infra', 'security'],
    'azureCosmosDb': ['cloud-infra', 'database', 'read-data', 'write-data'],
    'cloudflare': ['cloud-infra', 'developer', 'security'],
    'googleCloudNaturalLanguage': ['cloud-infra', 'ai-processor', 'analyze-text'],
    'googleFirebaseCloudFirestore': ['cloud-infra', 'database', 'read-data', 'write-data'],
    'googleFirebaseRealtimeDatabase': ['cloud-infra', 'database', 'read-data', 'write-data'],

    # ── AI / LLM Models ──
    'lmChatOpenAi': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatAnthropic': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatGoogleGemini': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatOllama': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatGroq': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatMistralCloud': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatDeepSeek': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatCohere': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatAzureOpenAi': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatXAiGrok': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatVercelAiGateway': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatAwsBedrock': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmChatGoogleVertex': ['ai-llm', 'chat-ai', 'generate-content'],
    'lmOpenAi': ['ai-llm', 'generate-content'],
    'lmOpenHuggingFaceInference': ['ai-llm', 'generate-content'],

    # ── AI Agent ──
    'agent': ['ai-agent', 'chat-ai', 'chatbot', 'generate-content'],
    'agentTool': ['ai-agent', 'ai-tool'],
    'openAiAssistant': ['ai-agent', 'chat-ai', 'chatbot'],
    'modelSelector': ['ai-llm', 'ai-agent'],
    'microsoftAgent365Trigger': ['ai-agent', 'trigger-on-chat'],

    # ── AI Embeddings ──
    'embeddingsOpenAi': ['ai-embedding', 'rag'],
    'embeddingsAzureOpenAi': ['ai-embedding', 'rag'],
    'embeddingsGoogleGemini': ['ai-embedding', 'rag'],
    'embeddingsGoogleVertex': ['ai-embedding', 'rag'],
    'embeddingsOllama': ['ai-embedding', 'rag'],
    'embeddingsCohere': ['ai-embedding', 'rag'],
    'embeddingsMistralCloud': ['ai-embedding', 'rag'],
    'embeddingsHuggingFaceInference': ['ai-embedding', 'rag'],
    'embeddingsAwsBedrock': ['ai-embedding', 'rag'],

    # ── AI Vector Stores ──
    'vectorStorePinecone': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreQdrant': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreChromaDB': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreWeaviate': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreSupabase': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStorePGVector': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreRedis': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreMongoDBAtlas': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreAzureAISearch': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreInMemory': ['ai-vectorstore', 'rag', 'search'],
    'vectorStoreInMemoryInsert': ['ai-vectorstore', 'rag', 'write-data'],
    'vectorStoreInMemoryLoad': ['ai-vectorstore', 'rag', 'read-data'],
    'vectorStoreZep': ['ai-vectorstore', 'rag', 'search', 'write-data'],
    'vectorStoreZepInsert': ['ai-vectorstore', 'rag', 'write-data'],
    'vectorStoreZepLoad': ['ai-vectorstore', 'rag', 'read-data'],
    'vectorStorePineconeInsert': ['ai-vectorstore', 'rag', 'write-data'],
    'vectorStorePineconeLoad': ['ai-vectorstore', 'rag', 'read-data'],
    'vectorStoreSupabaseInsert': ['ai-vectorstore', 'rag', 'write-data'],
    'vectorStoreSupabaseLoad': ['ai-vectorstore', 'rag', 'read-data'],
    'vectorStoreMilvus': ['ai-vectorstore', 'rag', 'search', 'write-data'],

    # ── AI Memory ──
    'memoryBufferWindow': ['ai-memory', 'chatbot', 'chat-ai'],
    'memoryRedisChat': ['ai-memory', 'chatbot', 'database'],
    'memoryPostgresChat': ['ai-memory', 'chatbot', 'database'],
    'memoryMongoDbChat': ['ai-memory', 'chatbot', 'database'],
    'memoryManager': ['ai-memory', 'chatbot'],
    'memoryChatRetriever': ['ai-memory', 'chatbot', 'read-data'],
    'memoryZep': ['ai-memory', 'chatbot'],
    'memoryMotorhead': ['ai-memory', 'chatbot'],
    'memoryXata': ['ai-memory', 'chatbot'],

    # ── AI Retrieval ──
    'retrieverVectorStore': ['ai-retrieval', 'rag', 'search'],
    'retrieverMultiQuery': ['ai-retrieval', 'rag', 'search'],
    'retrieverContextualCompression': ['ai-retrieval', 'rag', 'search'],
    'rerankerCohere': ['ai-retrieval', 'rag'],

    # ── AI Chains ──
    'chainLlm': ['ai-chain', 'generate-content', 'chat-ai'],
    'chainSummarization': ['ai-chain', 'analyze-text', 'generate-content'],
    'chainRetrievalQa': ['ai-chain', 'rag', 'chat-ai', 'search'],

    # ── AI Processors ──
    'informationExtractor': ['ai-processor', 'analyze-text', 'data-transform'],
    'textClassifier': ['ai-processor', 'analyze-text', 'filter-data'],
    'sentimentAnalysis': ['ai-processor', 'analyze-text'],
    'guardrails': ['ai-processor', 'security', 'filter-data'],

    # ── AI Output Parsers ──
    'outputParserStructured': ['ai-processor', 'data-transform'],
    'outputParserItemList': ['ai-processor', 'data-transform'],
    'outputParserAutofixing': ['ai-processor'],

    # ── AI Document/Text ──
    'documentDefaultDataLoader': ['ai-document', 'rag', 'file-process', 'document-processing'],
    'documentBinaryInputLoader': ['ai-document', 'rag', 'file-process'],
    'documentJsonInputLoader': ['ai-document', 'rag'],
    'documentGithubLoader': ['ai-document', 'rag', 'developer'],
    'textSplitterCharacterTextSplitter': ['ai-document', 'rag', 'data-transform'],
    'textSplitterRecursiveCharacterTextSplitter': ['ai-document', 'rag', 'data-transform'],
    'textSplitterTokenSplitter': ['ai-document', 'rag', 'data-transform'],

    # ── AI Tools ──
    'toolCalculator': ['ai-tool'],
    'toolCode': ['ai-tool', 'execute-code'],
    'toolThink': ['ai-tool'],
    'toolHttpRequest': ['ai-tool', 'call-api'],
    'toolWorkflow': ['ai-tool', 'manage-workflow'],
    'toolVectorStore': ['ai-tool', 'rag', 'search'],
    'toolWikipedia': ['ai-tool', 'search', 'read-data'],
    'toolExecutor': ['ai-tool'],
    'mcpClientTool': ['ai-tool', 'call-api'],
    'mcpClient': ['ai-tool', 'call-api'],

    # ── AI Chat / Triggers ──
    'chatTrigger': ['ai-agent', 'chatbot', 'trigger-on-chat', 'chat-ai'],
    'manualChatTrigger': ['ai-agent', 'chatbot', 'trigger-on-chat'],
    'mcpTrigger': ['ai-tool', 'trigger-on-webhook'],
    'chat': ['ai-agent', 'chatbot', 'chat-ai', 'send-message'],

    # ── AI Direct Provider Nodes ──
    'openAi': ['ai-llm', 'generate-content', 'analyze-text', 'video-audio'],
    'anthropic': ['ai-llm', 'generate-content', 'analyze-text', 'document-processing'],
    'googleGemini': ['ai-llm', 'generate-content', 'analyze-text', 'video-audio'],
    'ollama': ['ai-llm', 'generate-content', 'analyze-text'],
    'perplexity': ['ai-llm', 'search', 'generate-content', 'web-scraping'],
    'mistralAi': ['ai-llm', 'generate-content'],

    # ── ChatHub (internal) ──
    'chatHubVectorStorePinecone': ['ai-vectorstore', 'rag'],
    'chatHubVectorStoreQdrant': ['ai-vectorstore', 'rag'],
    'chatHubVectorStorePGVector': ['ai-vectorstore', 'rag'],

    # ── LangChain Code ──
    'code': ['execute-code'],  # Will be overridden for langchain.code specifically

    # ── E-commerce ──
    'stripe': ['ecommerce', 'read-data', 'write-data'],
    'stripeTrigger': ['ecommerce', 'trigger-on-event'],
    'shopify': ['ecommerce', 'read-data', 'write-data'],
    'shopifyTrigger': ['ecommerce', 'trigger-on-event'],
    'wooCommerce': ['ecommerce', 'read-data', 'write-data'],
    'wooCommerceTrigger': ['ecommerce', 'trigger-on-event'],
    'payPal': ['ecommerce', 'read-data'],
    'payPalTrigger': ['ecommerce', 'trigger-on-event'],
    'magento2': ['ecommerce', 'read-data', 'write-data'],
    'paddle': ['ecommerce', 'read-data'],
    'chargebee': ['ecommerce', 'read-data'],
    'chargebeeTrigger': ['ecommerce', 'trigger-on-event'],

    # ── Support ──
    'zendesk': ['support', 'support-automation', 'read-data', 'write-data'],
    'zendeskTrigger': ['support', 'trigger-on-event'],
    'freshdesk': ['support', 'support-automation', 'read-data', 'write-data'],
    'freshservice': ['support', 'support-automation', 'read-data', 'write-data'],
    'intercom': ['support', 'messaging', 'read-data', 'write-data'],
    'helpScout': ['support', 'read-data', 'write-data'],
    'helpScoutTrigger': ['support', 'trigger-on-event'],
    'drift': ['support', 'messaging', 'read-data'],

    # ── Scheduling / Calendar ──
    'scheduleTrigger': ['trigger-on-schedule', 'scheduling'],
    'cron': ['trigger-on-schedule', 'scheduling'],
    'interval': ['trigger-on-schedule', 'scheduling'],
    'googleCalendar': ['scheduling', 'read-data', 'write-data'],
    'googleCalendarTrigger': ['scheduling', 'trigger-on-event'],
    'calendlyTrigger': ['scheduling', 'trigger-on-event'],
    'calTrigger': ['scheduling', 'trigger-on-event'],
    'acuitySchedulingTrigger': ['scheduling', 'trigger-on-event'],

    # ── CMS ──
    'wordpress': ['cms', 'content-generation', 'read-data', 'write-data'],
    'ghost': ['cms', 'content-generation', 'read-data', 'write-data'],
    'strapi': ['cms', 'read-data', 'write-data'],
    'contentful': ['cms', 'read-data'],
    'webflow': ['cms', 'read-data', 'write-data'],
    'webflowTrigger': ['cms', 'trigger-on-event'],
    'cockpit': ['cms', 'read-data', 'write-data'],
    'googleDocs': ['cms', 'productivity', 'read-data', 'write-data'],

    # ── Voice / SMS ──
    'twilio': ['voice-sms', 'send-message', 'notification'],
    'twilioTrigger': ['voice-sms', 'trigger-on-event'],
    'vonage': ['voice-sms', 'send-message'],
    'plivo': ['voice-sms', 'send-message'],
    'messageBird': ['voice-sms', 'send-message'],
    'mocean': ['voice-sms', 'send-message'],

    # ── Queue / Messaging Infra ──
    'rabbitmq': ['queue', 'send-message'],
    'rabbitmqTrigger': ['queue', 'trigger-on-event'],
    'amqp': ['queue', 'send-message'],
    'amqpTrigger': ['queue', 'trigger-on-event'],
    'kafka': ['queue', 'send-message', 'data-pipeline'],
    'kafkaTrigger': ['queue', 'trigger-on-event'],
    'mqtt': ['queue', 'iot', 'send-message'],
    'mqttTrigger': ['queue', 'iot', 'trigger-on-event'],

    # ── IoT ──
    'homeAssistant': ['iot', 'read-data', 'write-data'],
    'philipsHue': ['iot', 'write-data'],

    # ── Form ──
    'formTrigger': ['form', 'trigger-on-form', 'form-processing'],
    'form': ['form', 'form-processing'],
    'formIoTrigger': ['form', 'trigger-on-form'],
    'formstackTrigger': ['form', 'trigger-on-form'],
    'jotFormTrigger': ['form', 'trigger-on-form'],
    'typeformTrigger': ['form', 'trigger-on-form'],
    'surveyMonkeyTrigger': ['form', 'trigger-on-form'],

    # ── Analytics ──
    'googleAnalytics': ['analytics', 'read-data'],
    'segment': ['analytics', 'write-data'],

    # ── Security ──
    'crypto': ['security', 'encrypt-sign'],
    'jwt': ['security', 'encrypt-sign'],
    'bitwarden': ['security', 'read-data'],
    'okta': ['security', 'read-data', 'write-data'],

    # ── Monitoring / Operations ──
    'sentryIo': ['developer', 'monitoring', 'read-data'],
    'pagerDuty': ['monitoring', 'notification', 'support'],
    'grafana': ['monitoring', 'analytics', 'read-data'],
    'uptimeRobot': ['monitoring', 'read-data'],

    # ── Utility Nodes ──
    'set': ['utility', 'data-transform', 'transform-data'],
    'if': ['flow-control', 'filter-data'],
    'switch': ['flow-control', 'filter-data'],
    'merge': ['flow-control', 'merge-data'],
    'filter': ['flow-control', 'filter-data'],
    'sort': ['flow-control', 'data-transform'],
    'limit': ['flow-control', 'filter-data'],
    'aggregate': ['data-transform', 'merge-data'],
    'summarize': ['data-transform', 'merge-data', 'report-generation'],
    'splitOut': ['data-transform', 'flow-control'],
    'splitInBatches': ['flow-control', 'loop-data'],
    'removeDuplicates': ['data-transform', 'filter-data'],
    'compareDatasets': ['data-transform', 'data-sync'],
    'renameKeys': ['data-transform'],
    'itemLists': ['data-transform', 'flow-control'],
    'wait': ['flow-control'],
    'noOp': ['flow-control'],
    'stopAndError': ['flow-control', 'error-handling'],
    'aiTransform': ['data-transform', 'ai-llm', 'generate-content'],

    # ── File Processing ──
    'extractFromFile': ['file-process', 'read-data', 'document-processing'],
    'convertToFile': ['file-process', 'file-convert'],
    'readPDF': ['file-process', 'document-processing', 'read-data'],
    'spreadsheetFile': ['file-process', 'spreadsheet', 'file-convert'],
    'compression': ['file-process', 'file-convert'],
    'editImage': ['file-process', 'content-generation'],
    'readWriteFile': ['file-process', 'file-upload', 'file-download'],
    'moveBinaryData': ['file-process', 'file-convert'],
    'html': ['file-process', 'data-transform', 'web-scraping'],
    'htmlExtract': ['file-process', 'web-scraping', 'data-transform'],
    'xml': ['file-process', 'data-transform'],
    'markdown': ['file-process', 'data-transform', 'content-generation'],

    # ── Network / API ──
    'httpRequest': ['utility', 'call-api', 'web-scraping', 'read-data', 'write-data'],
    'httpRequestTool': ['utility', 'call-api', 'ai-tool'],
    'webhook': ['trigger-on-webhook'],
    'respondToWebhook': ['trigger-on-webhook', 'send-message'],
    'graphql': ['utility', 'call-api', 'read-data'],

    # ── Workflow Meta ──
    'executeWorkflow': ['manage-workflow', 'flow-control'],
    'executeWorkflowTrigger': ['manage-workflow', 'trigger-on-event'],
    'executionData': ['manage-workflow', 'read-data'],
    'stickyNote': ['workflow-meta'],
    'debugHelper': ['workflow-meta', 'developer'],
    'timeSaved': ['workflow-meta', 'analytics'],
    'manualTrigger': ['trigger-on-event', 'utility'],
    'workflowTrigger': ['manage-workflow', 'trigger-on-event'],
    'n8nTrigger': ['manage-workflow', 'trigger-on-event'],
    'errorTrigger': ['error-handling', 'trigger-on-event', 'monitoring'],
    'evaluationTrigger': ['workflow-meta', 'trigger-on-event'],
    'simulateTrigger': ['workflow-meta', 'trigger-on-event'],
    'sseTrigger': ['trigger-on-event', 'trigger-on-webhook'],
    'boxTrigger': ['file-storage', 'trigger-on-event'],
    'wiseTrigger': ['ecommerce', 'trigger-on-event'],
    'flowTrigger': ['trigger-on-event'],

    # ── Misc Services ──
    'rssFeedRead': ['read-data', 'web-scraping', 'content-generation'],
    'rssFeedReadTrigger': ['trigger-on-event', 'web-scraping'],
    'phantombuster': ['web-scraping', 'social-media', 'lead-enrichment'],
    'airtop': ['web-scraping', 'read-data'],
    'mindee': ['document-processing', 'file-process'],
    'googleTranslate': ['data-transform', 'generate-content'],
    'deepL': ['data-transform', 'generate-content'],
    'zoom': ['video-audio', 'scheduling'],
    'disqus': ['social-media', 'read-data'],
    'hackerNews': ['social-media', 'read-data'],
    'quickbooks': ['ecommerce', 'read-data', 'write-data'],
    'xero': ['ecommerce', 'read-data', 'write-data'],
    'harvest': ['productivity', 'read-data', 'write-data'],
    'clockify': ['productivity', 'read-data', 'write-data'],
    'clockifyTrigger': ['productivity', 'trigger-on-event'],
    'togglTrigger': ['productivity', 'trigger-on-event'],
    'strava': ['social-media', 'read-data'],
    'npm': ['developer', 'read-data'],
    'bambooHr': ['productivity', 'read-data', 'write-data'],
    'workableTrigger': ['productivity', 'trigger-on-event'],
    'figmaTrigger': ['developer', 'trigger-on-event'],
    'googleBusinessProfileTrigger': ['analytics', 'trigger-on-event'],
    'postmarkTrigger': ['email', 'trigger-on-event'],
    'loneScale': ['crm', 'lead-enrichment'],
    'loneScaleTrigger': ['crm', 'trigger-on-event'],
    'koBoToolboxTrigger': ['form', 'trigger-on-event'],
    'customerIoTrigger': ['marketing', 'trigger-on-event'],
    'emeliaTrigger': ['marketing', 'trigger-on-event'],
    'urlScanIo': ['security', 'monitoring', 'web-scraping'],
    'securityScorecard': ['security', 'monitoring', 'read-data'],
    'splunk': ['monitoring', 'analytics', 'security', 'search'],
    'venafiTlsProtectCloud': ['security', 'cloud-infra'],
    'microsoftGraphSecurity': ['security', 'read-data'],

    'dhl': ['ecommerce', 'read-data'],
    'wise': ['ecommerce', 'read-data'],
    'profitWell': ['analytics', 'ecommerce', 'read-data'],
    'bitly': ['utility', 'marketing'],
    'rundeck': ['developer', 'cloud-infra', 'execute-code'],
    'keap': ['crm', 'marketing', 'read-data', 'write-data'],
    'syncroMsp': ['support', 'read-data', 'write-data'],
    'quickbase': ['spreadsheet', 'database', 'read-data', 'write-data'],
    'nocoDb': ['spreadsheet', 'database', 'read-data', 'write-data'],
    'elasticSecurity': ['security', 'monitoring'],
    'uproc': ['data-transform', 'read-data'],
    'openWeatherMap': ['utility', 'read-data'],
    'filemaker': ['database', 'read-data'],
    'marketstack': ['analytics', 'read-data'],
    'n8nTrainingCustomerDatastore': ['workflow-meta'],
    'evaluation': ['workflow-meta'],
}

# ─── AUTO-TAG RULES ─────────────────────────────────────────────────────────

def _get_suffix(node_type):
    """Get the part after the last dot in node_type."""
    return node_type.rsplit('.', 1)[-1] if '.' in node_type else node_type


def _auto_tags_from_operations(ops_json):
    """Derive action tags from operations JSON."""
    tags = set()
    if not ops_json or len(ops_json) < 5:
        return tags
    try:
        ops = json.loads(ops_json)
    except:
        return tags

    for op in ops:
        operation = (op.get('operation', '') or '').lower()
        resource = (op.get('resource', '') or '').lower()

        # Action tags from operations
        if operation in ('create', 'insert', 'push', 'add', 'upload'):
            tags.add('write-data')
        if operation in ('get', 'getall', 'read', 'list', 'search', 'download', 'select'):
            tags.add('read-data')
        if operation in ('update', 'upsert', 'patch', 'edit'):
            tags.add('update-data')
        if operation in ('delete', 'remove', 'archive'):
            tags.add('delete-data')
        if operation in ('send', 'post', 'notify', 'reply'):
            tags.add('send-message')
        if operation in ('search', 'query', 'find', 'lookup'):
            tags.add('search')

        # Resource-based use-case tags
        if resource in ('message', 'chat', 'chatmessage', 'channelmessage'):
            tags.add('messaging')
            tags.add('send-message')
        if resource in ('contact', 'lead', 'person', 'customer'):
            tags.add('crm')
        if resource in ('ticket', 'issue'):
            tags.add('support')
        if resource in ('invoice', 'payment', 'order'):
            tags.add('ecommerce')
        if resource in ('file', 'folder', 'document'):
            tags.add('file-storage')
        if resource in ('task', 'project'):
            tags.add('project-management')
        if resource in ('event', 'calendar', 'appointment'):
            tags.add('scheduling')
        if resource in ('post', 'article', 'page'):
            tags.add('content-generation')
        if resource in ('campaign', 'subscriber', 'list'):
            tags.add('marketing')
        if resource in ('user', 'member', 'team', 'group'):
            tags.add('read-data')
        if resource == 'row':
            tags.add('database')
        if resource in ('ai', 'text', 'image', 'audio', 'video'):
            tags.add('ai-llm')
            tags.add('generate-content')

    return tags


def _auto_tags_from_description(desc, name):
    """Derive tags from description and display name."""
    tags = set()
    if not desc:
        return tags
    desc_lower = desc.lower()
    name_lower = name.lower() if name else ''

    # Description-based detection
    if any(w in desc_lower for w in ['sends data', 'send message', 'send email', 'send sms', 'send notification']):
        tags.add('send-message')
        tags.add('notification')
    if any(w in desc_lower for w in ['trigger', 'starts the workflow', 'handle events']):
        tags.add('trigger-on-event')
    if 'webhook' in desc_lower:
        tags.add('trigger-on-webhook')
    if any(w in desc_lower for w in ['scrape', 'crawl', 'extract from']):
        tags.add('web-scraping')
    if any(w in desc_lower for w in ['ai agent', 'action plan', 'language model', 'llm', 'chat model']):
        tags.add('ai-llm')
    if 'vector store' in desc_lower or 'vector search' in desc_lower:
        tags.add('ai-vectorstore')
        tags.add('rag')
    if 'embedding' in desc_lower:
        tags.add('ai-embedding')
        tags.add('rag')
    if any(w in desc_lower for w in ['memory', 'conversation history', 'chat history']):
        tags.add('ai-memory')
        tags.add('chatbot')
    if any(w in desc_lower for w in ['classify', 'classification', 'categorize']):
        tags.add('ai-processor')
        tags.add('analyze-text')
    if any(w in desc_lower for w in ['summariz', 'summary']):
        tags.add('ai-chain')
        tags.add('analyze-text')
    if any(w in desc_lower for w in ['pdf', 'document', 'invoice', 'receipt']):
        tags.add('document-processing')
    if any(w in desc_lower for w in ['api', 'http request', 'rest']):
        tags.add('call-api')

    return tags


def _auto_tags_from_ai_summary(summary_json):
    """Derive tags from AI-generated documentation summary."""
    tags = set()
    if not summary_json:
        return tags
    try:
        summary = json.loads(summary_json)
    except:
        return tags

    if isinstance(summary, dict):
        purpose = (summary.get('purpose', '') or '').lower()
        capabilities = summary.get('capabilities', [])

        # Derive from purpose
        if any(w in purpose for w in ['whatsapp', 'sms', 'message', 'notification', 'chat']):
            tags.add('messaging')
            tags.add('send-message')
        if any(w in purpose for w in ['email', 'mail']):
            tags.add('email')
        if any(w in purpose for w in ['crm', 'contact', 'lead']):
            tags.add('crm')
        if any(w in purpose for w in ['pdf', 'document', 'invoice']):
            tags.add('document-processing')
        if any(w in purpose for w in ['scrape', 'crawl', 'extract']):
            tags.add('web-scraping')
        if any(w in purpose for w in ['ai', 'llm', 'model', 'gpt', 'openai']):
            tags.add('ai-llm')
        if any(w in purpose for w in ['database', 'sql', 'store data']):
            tags.add('database')
        if any(w in purpose for w in ['payment', 'billing', 'invoice', 'subscription']):
            tags.add('ecommerce')
        if any(w in purpose for w in ['image', 'photo', 'screenshot']):
            tags.add('content-generation')
        if any(w in purpose for w in ['video', 'audio', 'speech', 'voice']):
            tags.add('video-audio')

    return tags


def generate_tags(node):
    """Generate complete tag set for a single node."""
    node_type = node['node_type']
    suffix = _get_suffix(node_type)

    tags = set()

    # 1. Explicit mapping (highest priority)
    # Try exact suffix first, then without common suffixes
    base_suffix = suffix
    for strip_suffix in ['Tool', 'HitlTool', 'Trigger']:
        if base_suffix.endswith(strip_suffix) and base_suffix != strip_suffix:
            base_suffix = base_suffix[:-len(strip_suffix)]
            break

    if suffix in EXPLICIT_TAGS:
        tags.update(EXPLICIT_TAGS[suffix])
    elif base_suffix in EXPLICIT_TAGS:
        # Inherit base node tags for tool/trigger variants
        tags.update(EXPLICIT_TAGS[base_suffix])

    # 2. Auto-tags from operations
    tags.update(_auto_tags_from_operations(node.get('operations')))

    # 3. Auto-tags from description + name
    tags.update(_auto_tags_from_description(node.get('description'), node.get('display_name')))

    # 4. Auto-tags from AI summary (community nodes)
    tags.update(_auto_tags_from_ai_summary(node.get('ai_documentation_summary')))

    # 5. Structural tags from flags
    if node.get('is_trigger'):
        tags.add('trigger-on-event')
    if node.get('is_tool_variant'):
        tags.add('ai-tool')
    if node.get('is_webhook'):
        tags.add('trigger-on-webhook')
    if node.get('is_community'):
        tags.add('community')
    if node.get('is_verified'):
        tags.add('verified')

    # 6. Package-based tags for langchain nodes
    if 'langchain' in node_type:
        if not any(t.startswith('ai-') for t in tags):
            tags.add('ai-llm')  # Default for langchain nodes

    # 7. Ensure at least one tag
    if not tags:
        # Fallback based on category
        cat = (node.get('category') or '').lower()
        if cat == 'trigger':
            tags.add('trigger-on-event')
        elif cat == 'transform':
            tags.add('data-transform')
        elif cat == 'input':
            tags.add('read-data')
        elif cat == 'output':
            tags.add('write-data')
        elif cat == 'community':
            tags.add('community')
        else:
            tags.add('utility')

    return sorted(tags)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Add tags column if it doesn't exist
    try:
        cur.execute("ALTER TABLE nodes ADD COLUMN tags TEXT DEFAULT ''")
        conn.commit()
        print("Added 'tags' column to nodes table")
    except sqlite3.OperationalError:
        print("'tags' column already exists")

    # Fetch all nodes
    cur.execute("""
        SELECT node_type, display_name, description, category,
               is_trigger, is_ai_tool, is_tool_variant, is_webhook,
               is_community, is_verified, operations, ai_documentation_summary
        FROM nodes
    """)
    rows = cur.fetchall()
    print(f"Processing {len(rows)} nodes...")

    stats = {
        'total': 0,
        'explicit': 0,
        'auto_only': 0,
        'fallback': 0,
        'avg_tags': 0,
        'tag_counts': {},
    }

    for row in rows:
        node = {
            'node_type': row[0],
            'display_name': row[1],
            'description': row[2],
            'category': row[3],
            'is_trigger': row[4],
            'is_ai_tool': row[5],
            'is_tool_variant': row[6],
            'is_webhook': row[7],
            'is_community': row[8],
            'is_verified': row[9],
            'operations': row[10],
            'ai_documentation_summary': row[11],
        }

        tags = generate_tags(node)
        tags_str = ', '.join(tags)

        cur.execute("UPDATE nodes SET tags = ? WHERE node_type = ?", (tags_str, node['node_type']))

        stats['total'] += 1
        stats['avg_tags'] += len(tags)
        for t in tags:
            stats['tag_counts'][t] = stats['tag_counts'].get(t, 0) + 1

        suffix = _get_suffix(node['node_type'])
        if suffix in EXPLICIT_TAGS:
            stats['explicit'] += 1

    conn.commit()
    conn.close()

    stats['avg_tags'] = stats['avg_tags'] / stats['total'] if stats['total'] else 0

    print(f"\nDone! Tagged {stats['total']} nodes")
    print(f"  Avg tags per node: {stats['avg_tags']:.1f}")
    print(f"  Explicit mappings used: {stats['explicit']}")
    print(f"\nTop 30 tags by frequency:")
    for tag, count in sorted(stats['tag_counts'].items(), key=lambda x: -x[1])[:30]:
        print(f"  {tag}: {count}")


if __name__ == '__main__':
    main()
