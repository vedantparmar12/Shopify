import os
import json
import re
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import openai
from anthropic import Anthropic
import google.generativeai as genai

from app.models.brand_insights import FAQ
from app.utils.exceptions import LLMServiceException

load_dotenv()


class LLMService:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        self.use_llm = bool(self.openai_api_key or self.anthropic_api_key or self.gemini_api_key)
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-pro'))
            self.llm_provider = 'gemini'
        elif self.openai_api_key:
            openai.api_key = self.openai_api_key
            self.llm_provider = 'openai'
        elif self.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
            self.llm_provider = 'anthropic'
        else:
            self.llm_provider = None
    
    async def structure_faq_data(self, raw_text: str) -> List[FAQ]:
        if not self.use_llm or not raw_text:
            return self._fallback_faq_parser(raw_text)
        
        prompt = f"""
        Extract FAQ pairs from the following text. Return a JSON array of objects with 'question' and 'answer' fields.
        Only include actual questions and their answers, not general text.
        
        Text:
        {raw_text[:3000]}
        
        Return format:
        [
            {{"question": "...", "answer": "..."}},
            ...
        ]
        """
        
        try:
            response = await self._call_llm(prompt)
            faqs_data = json.loads(response)
            
            faqs = []
            for item in faqs_data:
                if isinstance(item, dict) and 'question' in item and 'answer' in item:
                    faqs.append(FAQ(
                        question=item['question'][:200],
                        answer=item['answer'][:500]
                    ))
            
            return faqs[:20]
        except Exception as e:
            return self._fallback_faq_parser(raw_text)
    
    async def extract_brand_context(self, page_content: str) -> str:
        if not self.use_llm or not page_content:
            return self._fallback_brand_context(page_content)
        
        prompt = f"""
        Summarize the brand story and key information from this content in 2-3 paragraphs.
        Focus on: company mission, values, history, what makes them unique.
        
        Content:
        {page_content[:3000]}
        
        Provide a concise summary:
        """
        
        try:
            response = await self._call_llm(prompt)
            return response[:2000]
        except Exception:
            return self._fallback_brand_context(page_content)
    
    async def clean_policy_text(self, raw_policy: str) -> str:
        if not self.use_llm or not raw_policy:
            return self._clean_text(raw_policy)
        
        if len(raw_policy) < 500:
            return self._clean_text(raw_policy)
        
        prompt = f"""
        Clean and summarize this policy document. Keep the most important points.
        Remove navigation elements, headers, footers, and redundant text.
        Maintain key policy details and terms.
        
        Policy text:
        {raw_policy[:3000]}
        
        Cleaned summary:
        """
        
        try:
            response = await self._call_llm(prompt)
            return response[:3000]
        except Exception:
            return self._clean_text(raw_policy)
    
    async def categorize_products(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        if not self.use_llm or not products:
            return self._fallback_categorize(products)
        
        product_names = [p.get('name', '') for p in products[:50]]
        
        prompt = f"""
        Categorize these products into logical groups. Return a JSON object with category names as keys.
        
        Products:
        {json.dumps(product_names)}
        
        Return format:
        {{
            "Category Name": ["product1", "product2"],
            ...
        }}
        """
        
        try:
            response = await self._call_llm(prompt)
            # Clean response for JSON parsing (especially for Gemini)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            categories = json.loads(response)
            
            categorized = {}
            for category, product_list in categories.items():
                categorized[category] = [
                    p for p in products 
                    if p.get('name', '') in product_list
                ]
            
            return categorized
        except Exception:
            return self._fallback_categorize(products)
    
    async def _call_llm(self, prompt: str) -> str:
        try:
            if self.llm_provider == 'gemini' and genai:
                # Google Gemini API
                generation_config = {
                    "temperature": float(os.getenv('GEMINI_TEMPERATURE', '0.3')),
                    "max_output_tokens": int(os.getenv('GEMINI_MAX_TOKENS', '1000')),
                }
                
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                return response.text
            
            elif self.llm_provider == 'openai':
                response = openai.ChatCompletion.create(
                    model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that extracts and structures e-commerce data."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
                    temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.3'))
                )
                return response.choices[0].message.content
            
            elif self.llm_provider == 'anthropic':
                response = self.anthropic_client.messages.create(
                    model=os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                    max_tokens=int(os.getenv('ANTHROPIC_MAX_TOKENS', '1000')),
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
            else:
                raise LLMServiceException("No LLM provider configured")
        
        except Exception as e:
            raise LLMServiceException(f"LLM call failed: {str(e)}")
    
    def _fallback_faq_parser(self, raw_text: str) -> List[FAQ]:
        faqs = []
        
        # Simple pattern matching for Q&A format
        lines = raw_text.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line looks like a question
            if any(line.startswith(q) for q in ['Q:', 'Question:', 'Q.']) or line.endswith('?'):
                if current_question and current_answer:
                    faqs.append(FAQ(
                        question=current_question[:200],
                        answer=' '.join(current_answer)[:500]
                    ))
                
                current_question = re.sub(r'^(Q:|Question:|Q\.)\s*', '', line)
                current_answer = []
            
            elif any(line.startswith(a) for a in ['A:', 'Answer:', 'A.']):
                answer_text = re.sub(r'^(A:|Answer:|A\.)\s*', '', line)
                current_answer.append(answer_text)
            
            elif current_question and len(current_answer) < 3:
                current_answer.append(line)
        
        # Add last Q&A pair
        if current_question and current_answer:
            faqs.append(FAQ(
                question=current_question[:200],
                answer=' '.join(current_answer)[:500]
            ))
        
        return faqs[:20]
    
    def _fallback_brand_context(self, page_content: str) -> str:
        # Simple extraction of first few paragraphs
        cleaned = self._clean_text(page_content)
        paragraphs = [p for p in cleaned.split('\n\n') if len(p) > 50]
        return '\n\n'.join(paragraphs[:3])[:2000]
    
    def _clean_text(self, text: str) -> str:
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common navigation elements
        text = re.sub(r'(Menu|Navigation|Footer|Header|Cookie.*?accept)', '', text, flags=re.IGNORECASE)
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        return text.strip()
    
    def _fallback_categorize(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        # Simple categorization based on product types
        categories = {}
        
        for product in products:
            product_type = product.get('product_type', 'Other')
            if not product_type:
                product_type = 'Other'
            
            if product_type not in categories:
                categories[product_type] = []
            
            categories[product_type].append(product)
        
        return categories