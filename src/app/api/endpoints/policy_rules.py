"""
Policy Rules API Endpoints

API endpoints for uploading policy documents and generating collection rules using AI.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_db, get_current_user
from app.db import models
from app.services.policy_rule_generator import PolicyRuleGenerator
from app.utils.pdf_processor import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


class PolicyUploadRequest(BaseModel):
    policy_type: str = "collection"
    policy_name: str
    description: Optional[str] = None


class RuleGenerationResponse(BaseModel):
    success: bool
    message: str
    rules_generated: int
    rules_saved: int
    saved_rule_ids: List[int]
    policy_analysis: Dict[str, Any]
    generation_timestamp: str
    rule_categories: List[str]


@router.post("/upload-policy", response_model=RuleGenerationResponse)
async def upload_policy_and_generate_rules(
    policy_file: UploadFile = File(...),
    policy_type: str = Form("collection"),
    policy_name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a policy document and automatically generate collection rules using AI.
    
    Supports PDF and text files. The AI will analyze the policy content and generate
    specific, actionable collection rules that map customer conditions to appropriate actions.
    """
    try:
        logger.info(f"=== POLICY UPLOAD AND RULE GENERATION ===")
        logger.info(f"User: {current_user.email}")
        logger.info(f"Policy file: {policy_file.filename}")
        logger.info(f"Policy type: {policy_type}")
        logger.info(f"Policy name: {policy_name}")
        
        # Validate file type
        if not policy_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = policy_file.filename.lower().split('.')[-1]
        if file_extension not in ['pdf', 'txt', 'doc', 'docx']:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload PDF, TXT, DOC, or DOCX files."
            )
        
        # Read file content
        file_content = await policy_file.read()
        
        # Extract text based on file type
        if file_extension == 'pdf':
            try:
                policy_text = extract_text_from_pdf(file_content)
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to extract text from PDF file")
        else:
            # For text files, decode directly
            try:
                policy_text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    policy_text = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Unable to decode text file")
        
        # Validate extracted content
        if not policy_text or len(policy_text.strip()) < 100:
            raise HTTPException(
                status_code=400, 
                detail="Policy document appears to be empty or too short for analysis"
            )
        
        logger.info(f"Extracted policy text: {len(policy_text)} characters")
        
        # Generate rules using AI
        rule_generator = PolicyRuleGenerator(db)
        result = rule_generator.generate_and_save_rules(policy_text, policy_type)
        
        # Save policy document metadata
        policy_document = models.PolicyDocument(
            name=policy_name,
            type=policy_type,
            description=description,
            filename=policy_file.filename,
            content=policy_text,
            rules_generated=result["rules_generated"],
            uploaded_by=current_user.id
        )
        
        db.add(policy_document)
        db.commit()
        
        logger.info(f"✅ Policy uploaded and {result['rules_generated']} rules generated successfully")
        
        return RuleGenerationResponse(
            success=True,
            message=f"Successfully generated {result['rules_generated']} rules from policy document",
            rules_generated=result["rules_generated"],
            rules_saved=result["rules_saved"],
            saved_rule_ids=result["saved_rule_ids"],
            policy_analysis=result["policy_analysis"],
            generation_timestamp=result["generation_timestamp"],
            rule_categories=result["rule_categories"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in policy upload and rule generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process policy document: {str(e)}")


@router.post("/generate-rules-from-text")
async def generate_rules_from_text(
    policy_text: str,
    policy_type: str = "collection",
    policy_name: str = "Manual Policy Input",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate collection rules from policy text input (for testing or manual input).
    """
    try:
        if not policy_text or len(policy_text.strip()) < 50:
            raise HTTPException(
                status_code=400, 
                detail="Policy text is too short for meaningful analysis"
            )
        
        logger.info(f"Generating rules from text input: {len(policy_text)} characters")
        
        # Generate rules using AI
        rule_generator = PolicyRuleGenerator(db)
        result = rule_generator.generate_and_save_rules(policy_text, policy_type)
        
        return {
            "success": True,
            "message": f"Successfully generated {result['rules_generated']} rules from policy text",
            "rules_generated": result["rules_generated"],
            "rules_saved": result["rules_saved"],
            "policy_analysis": result["policy_analysis"],
            "rule_categories": result["rule_categories"]
        }
        
    except Exception as e:
        logger.error(f"Error generating rules from text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate rules: {str(e)}")


@router.get("/generated-rules")
async def get_generated_rules(
    policy_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get list of generated collection rules with optional filtering.
    """
    try:
        query = db.query(models.CollectionRule).filter(
            models.CollectionRule.rule_type == "collection"
        )
        
        if policy_type:
            # Filter by conditions containing policy type info
            query = query.filter(models.CollectionRule.conditions.contains(policy_type))
        
        if is_active is not None:
            query = query.filter(models.CollectionRule.is_active == is_active)
        
        rules = query.order_by(models.CollectionRule.created_at.desc()).offset(offset).limit(limit).all()
        
        rules_data = []
        for rule in rules:
            rule_data = {
                "id": rule.id,
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type,
                "conditions": json.loads(rule.conditions) if rule.conditions else {},
                "actions": json.loads(rule.actions) if rule.actions else [],
                "priority": rule.priority,
                "is_active": rule.is_active,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None
            }
            rules_data.append(rule_data)
        
        return {
            "success": True,
            "rules": rules_data,
            "total_rules": len(rules_data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching generated rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch rules: {str(e)}")


@router.get("/policy-documents")
async def get_policy_documents(
    policy_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get list of uploaded policy documents.
    """
    try:
        query = db.query(models.PolicyDocument)
        
        if policy_type:
            query = query.filter(models.PolicyDocument.type == policy_type)
        
        documents = query.order_by(models.PolicyDocument.created_at.desc()).offset(offset).limit(limit).all()
        
        documents_data = []
        for doc in documents:
            doc_data = {
                "id": doc.id,
                "name": doc.name,
                "type": doc.type,
                "description": doc.description,
                "filename": doc.filename,
                "rules_generated": doc.rules_generated,
                "uploaded_by": doc.uploaded_by,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "content_length": len(doc.content) if doc.content else 0
            }
            documents_data.append(doc_data)
        
        return {
            "success": True,
            "documents": documents_data,
            "total_documents": len(documents_data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching policy documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@router.put("/rules/{rule_id}/toggle")
async def toggle_rule_status(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Toggle the active status of a generated rule.
    """
    try:
        rule = db.query(models.CollectionRule).filter(models.CollectionRule.id == rule_id).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        rule.is_active = not rule.is_active
        db.commit()
        
        return {
            "success": True,
            "message": f"Rule {rule.rule_name} {'activated' if rule.is_active else 'deactivated'}",
            "rule_id": rule_id,
            "is_active": rule.is_active
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling rule status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle rule status: {str(e)}")
