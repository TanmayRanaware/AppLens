"""Graph routes"""
from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from app.routes.auth import get_current_user
from app.db.base import get_db
from app.db.models import Service, Interaction, Repository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

router = APIRouter()


@router.get("/")
async def get_graph(
    repos: Optional[List[str]] = Query(None),
    request: Request = None,
):
    """Get graph data for visualization"""
    get_current_user(request)  # Verify auth
    
    async for session in get_db():
        # Build query for services
        service_query = select(Service)
        
        if repos:
            # Filter by repositories
            repo_result = await session.execute(
                select(Repository.id).where(Repository.full_name.in_(repos))
            )
            repo_ids = [r for r in repo_result.scalars().all()]
            if repo_ids:
                service_query = service_query.where(Service.repo_id.in_(repo_ids))
        
        services_result = await session.execute(service_query)
        services = services_result.scalars().all()
        
        # Build query for interactions
        interaction_query = select(Interaction)
        if repos:
            service_ids = [s.id for s in services]
            if service_ids:
                interaction_query = interaction_query.where(
                    and_(
                        Interaction.source_service_id.in_(service_ids),
                        Interaction.target_service_id.in_(service_ids),
                    )
                )
        
        interactions_result = await session.execute(interaction_query)
        interactions = interactions_result.scalars().all()
        
        # Get service stats (in/out degree)
        service_stats = {}
        for interaction in interactions:
            source_id = str(interaction.source_service_id)
            target_id = str(interaction.target_service_id)
            service_stats.setdefault(source_id, {"inDegree": 0, "outDegree": 0})
            service_stats.setdefault(target_id, {"inDegree": 0, "outDegree": 0})
            service_stats[source_id]["outDegree"] += 1
            service_stats[target_id]["inDegree"] += 1
        
        # Build nodes
        nodes = []
        service_map = {}
        for service in services:
            service_id = str(service.id)
            service_map[service.id] = service_id
            
            # Get repo info
            repo_result = await session.execute(
                select(Repository).where(Repository.id == service.repo_id)
            )
            repo = repo_result.scalar_one()
            
            stats = service_stats.get(service_id, {"inDegree": 0, "outDegree": 0})
            
            # Debug: Check service.name before adding to nodes
            service_name = service.name
            if not service_name or service_name.strip() == '':
                print(f"⚠️ WARNING: Service {service_id} has empty name! Service object: {service}")
            
            node_data = {
                "id": service_id,
                "name": service_name,  # Use the checked service_name
                "group": repo.full_name,  # Use repo as group for auto-coloring
                "repo": repo.full_name,
                "language": service.language or "unknown",
                "inDegree": stats["inDegree"],
                "outDegree": stats["outDegree"],
                "url": repo.html_url,
            }
            
            # Debug: Log first few nodes
            if len(nodes) < 3:
                print(f"🔍 Building node {len(nodes)}: {node_data}")
            
            nodes.append(node_data)
        
        # Build links
        # Track bidirectional HTTP edges (if A->B and B->A exist, mark as bidirectional)
        link_map = {}  # (source_id, target_id) -> link data
        links = []
        
        for interaction in interactions:
            source_id = service_map.get(interaction.source_service_id)
            target_id = service_map.get(interaction.target_service_id)
            
            if source_id and target_id:
                # For HTTP: Check if reverse edge exists (bidirectional)
                is_bidirectional = False
                if interaction.edge_type.value == "HTTP":
                    reverse_key = (target_id, source_id)
                    if reverse_key in link_map:
                        # Mark both as bidirectional
                        link_map[reverse_key]["bidirectional"] = True
                        is_bidirectional = True
                
                link = {
                    "source": source_id,
                    "target": target_id,
                    "kind": interaction.edge_type.value,  # Use 'kind' for linkAutoColorBy
                    "type": interaction.edge_type.value,  # Keep for backward compatibility
                    "confidence": interaction.confidence,
                    "bidirectional": is_bidirectional,
                }
                
                if interaction.edge_type.value == "HTTP":
                    link["method"] = interaction.http_method
                    link["url"] = interaction.http_url
                    link["via"] = interaction.http_url  # Use 'via' for link labels
                elif interaction.edge_type.value == "Kafka":
                    link["topic"] = interaction.kafka_topic
                    link["via"] = interaction.kafka_topic  # Use 'via' for link labels
                
                link_map[(source_id, target_id)] = link
                links.append(link)
        
        return {"nodes": nodes, "links": links}

