#!/usr/bin/env python3
"""
Dialogue Relation Extraction with Coreference Resolution - GPT-4.1 Optimized
Specialized for multi-speaker dialogue text with advanced GPT-4.1
"""
import os
import json
import re
import time, random
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Iterable, DefaultDict


import asyncio
from uuid import uuid4, UUID

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from memmachine.common.vector_graph_store import Node, Edge
from memmachine.common.vector_graph_store.neo4j_vector_graph_store import Neo4jVectorGraphStore, Neo4jVectorGraphStoreParams
from memmachine.common.embedder.openai_embedder import OpenAIEmbedder
from memmachine.common.language_model.openai_language_model import OpenAILanguageModel

os.environ["DSPY_CACHEDIR"] = "/tmp/dspy_cache"
import dspy

sem = asyncio.Semaphore(200)

filtered_dataset_path = "/home/tomz/graphiti/data/dev-filter-gpt-5-nano.json"
locomo_path = "/home/tomz/locomo/data/locomo10.json"
filtered_locomo_qa_path = "/home/tomz/locomo/data/filtered-locomo10-qa-gpt5-nano.json"
edge_extractor = None
entity_extractor = None
starting_test_case = 1
start = time.perf_counter()

# def get_available_model(env_var: str, model: str) -> str:
#     """Get available model - only GPT-4.1, no fallback."""
#     # Only use GPT-4.1, no fallback models
#     try:
#         lm = dspy.LM(model=model, api_key=os.getenv("OPENAI_API_KEY"), max_tokens=16000)
#         # Simple test call
#         test_result = lm("test")
#         print(f"✅ Using model: {model}")
#         return model
#     except Exception as e:
#         print(f"❌ Model {model} not available: {str(e)[:100]}...")
#         raise Exception(f"{model} is required but not available: {e}")

def init_dspy():
    # DSPy cache does not work on network filesystem, set to /tmp
    dspy_cache_dir = "/tmp/dspy_cache"
    if not os.path.exists(dspy_cache_dir):
        os.makedirs(dspy_cache_dir)
    os.environ["DSPY_CACHEDIR"] = dspy_cache_dir
    import dspy
    
    # Check if DSPy is available
    dspy.configure_cache(enable_disk_cache=True, enable_memory_cache=True, disk_cache_dir="/tmp/dspy_cache")
    print("✅ DSPy available")
    # Configure DSPy with OpenAI - use GPT-4.1 only
    # GPT-4.1 offers advanced reasoning and relation extraction capabilities
    # model_name = get_available_model("RE_LM_MODEL", model)
    
    # Use GPT-4.1 directly
    lm = dspy.LM(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"), max_tokens=16000)
    
    dspy.settings.configure(lm=lm)

def setup_dialogue_relation_extractor():
    """Setup DSPy-optimized relation extractor for dialogue text with coreference resolution"""
    """
    (extra)
    2. There are two input sections: PREVIOUS_MESSAGES and CURRENT_MESSAGES
           a) PREVIOUS_MESSAGES could be empty or contain multiple prior messages
           b) PREVIOUS_MESSAGES may or may not relate to CURRENT_MESSAGES
           c) Distinguish if a message from PREVIOUS_MESSAGES is related to CURRENT_MESSAGES or not 
           d) If an entity or relation in PREVIOUS_MESSAGES is not related to CURRENT_MESSAGES, do not extract it
    """
    class EdgeExtraction(dspy.Signature):
        """
        Extract semantic relationships from dialogue text with advanced coreference resolution. Return as JSON array.
        
        Guidelines:
        1. Extract meaningful semantic relationships between entities in dialogue
        2. Resolve complex coreferences in multi-speaker conversations:
           a) Identify all pronouns, definite articles, and vague references (the, this, that, it, they, etc.)
           b) Trace each reference back to its most specific antecedent in the conversation
           c) Replace vague references with the most specific, concrete entity name possible
           d) For events/actions, create descriptive names that capture the essence
        3. Handle speaker-specific references:
           - Resolve possessive pronouns and contextual references to specific person names when possible 
           - Identify relationships between speakers and mentioned entities
           - Track entity mentions across multiple speakers
        4. Pay special attention to temporal relationships and time information:
           - Extract when events occurred (dates, times, periods)
           - Preserve temporal context in relationships
           - Include time information in event descriptions
        5. Use context clues to determine the most appropriate entity name
        6. For people and organizations, always use their full, proper names when available
        7. Create meaningful event names that describe what actually happened
        8. Avoid extracting relationships where subject/object are still vague references
        9. Double-check that all entities are specific and unambiguous
        10. Return as JSON array of objects with "subject", "relation", "object" fields
        11. Make sure the resulting JSON is valid and parsable
        
        Coreference Resolution Strategy:
        - Replace any vague or ambiguous references with specific entity names based on conversation context
        - For events and actions, create descriptive names that capture what actually happened
        - For people and organizations, use their full, proper names when available
        - Always preserve temporal information and context
        - Handle speaker-specific references and possessive pronouns
        """
        text: str = dspy.InputField(desc="Input dialogue text to extract relationships from")
        relations: str = dspy.OutputField(desc="JSON array of relationships with subject, relation, object")
    
    # Create the edge predictor
    edge_predictor = dspy.Predict(EdgeExtraction)
    
    return edge_predictor

def setup_entity_extractor():
    """Setup DSPy-optimized entity extractor for entity extraction"""

    class EntityExtraction(dspy.Signature):
        """
        Extract entities from text. If QUERY is given, focus on entities relevant to the QUERY.

        Guidelines:
        1. The entities should be an object such as names, places, organizations, events, dates, etc.
        2. If the given text is a question:
           - Extract the subject and key objects mentioned in the question
           - Extract the entities that are likely have information relevant to answering the question
        3. Be as specific as possible when extracting entity names:
           - If a full name is given, extract the full name
           - If a location is given, extract the location
           - No need to extract relations, only entity names
        4. For people and organizations, always use their full, proper names when available
        5. Double-check that all entities are specific and unambiguous
        6. If QUERY is provided, only extract entities relevant to the QUERY
        7. Return as JSON array of entity names

        Coreference Resolution Strategy:
        - Replace any vague or ambiguous references with specific entity names based on conversation context
        - For events and actions, create descriptive names that capture what actually happened
        - For people and organizations, use their full, proper names when available
        - Always preserve temporal information and context
        - Handle speaker-specific references and possessive pronouns
        """
        text: str = dspy.InputField(desc="Input text to extract entities from")
        query: str = dspy.InputField(desc="Optional query to focus entity extraction on relevant entities")
        entities: str = dspy.OutputField(desc="JSON array of entity name strings")
        
    # Create the entity predictor
    entity_predictor = dspy.Predict(EntityExtraction)
    
    return entity_predictor


async def extract_dialogue_relations(text: str) -> List[Tuple[str, str, str]]:
    """Extract relations from dialogue text using DSPy-optimized method with coreference resolution"""
    global edge_extractor
    
    # Setup edge_extractor
    if edge_extractor is None:
        edge_extractor = setup_dialogue_relation_extractor()

    lm = dspy.LM(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"), max_tokens=16000)
    
    # Extract relations
    with dspy.settings.context(lm=lm):
        async with sem:
            result = await edge_extractor.acall(text=text)
    
    try:
        # Parse JSON response
        relations = json.loads(result.relations)
        triples = []
        for rel in relations:
            if all(key in rel for key in ['subject', 'relation', 'object']):
                triples.append((rel['subject'], rel['relation'], rel['object']))
        return triples
    except Exception as e:
        print(f"Warning: Failed to parse relations from text({text}), relation result({result.relations}): {str(e)}")
        raise e

def extract_entities(text: str, query: str = "") -> List[str]:
    global entity_extractor
    
    if entity_extractor is None:
        entity_extractor = setup_entity_extractor()
    
    lm = dspy.LM(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"), max_tokens=16000)
    with dspy.settings.context(lm=lm):
        result = entity_extractor(text=text, query=query)
        try:
            entities = json.loads(result.entities)
            return entities
        except Exception as e:
            print(f"Warning: Failed to parse entities from text({text}) with query({query}), result({result.entities}): {str(e)}")
            return []

def load_data(
    start_line: int = 1,
    num_cases: int = 100,
    randomize: bool = True,
):
    global filtered_dataset_path
    print(f"Loading data from line {start_line} to {num_cases}, randomize={randomize}")
    contexts = []
    questions = []
    answers = []
    i = 1
    with open(filtered_dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if i < start_line:
                i += 1
                continue
            if i > num_cases:
                break

            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["context"] = json.loads(obj["context"])
            for key, sentences in obj["context"]:
                context = f"{key}:\n"
                for s in sentences:
                    context += s + "\n"

                if randomize:
                    insert_index = random.randrange(len(contexts) + 1)  # 0..len inclusive
                    contexts.insert(insert_index, context)
                else:
                    contexts.append(context)

            questions.append(obj["question"])
            answers.append(obj["answer"])
            i += 1
    return contexts, questions, answers

def load_locomo10_raw(path: str) -> Tuple[List[List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """
    Returns:
      qa: list of QA dicts so you can do qa[0]['question'], qa[1]['answer'], ...
      conversations: list of a dictionary where each item is:
          {
            "timestamps": [session_1_date_time, session_2_date_time, ...], # each timestamp is a python datetime
            "sessions":   [session_1, session_2, ...]   # each session is a list of {speaker, text, ...}
          }, ...
    """
    TS_FMT = "%I:%M %p on %d %B, %Y"  # e.g., "1:14 pm on 25 May, 2023"
    records = None

    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # dataset might be a list of conversations or wrapped in a dict
    if not isinstance(records, list):
        raise ValueError("Unexpected LoCoMo JSON structure: expected a list of conversations")

    conversations: List[Dict[str, Any]] = []
    qas: List[List[Dict[str, Any]]] = []
    for rec in records:
        qa = rec["qa"]
        for q in qa:
            if "answer" not in q:
                if "adversarial_answer" in q:
                    q["answer"] = q["adversarial_answer"]
                else:
                    raise ValueError("Unexpected QA structure: missing 'answer' field")
        qas.append(qa)
        
        conv = rec["conversation"]
        if not isinstance(conv, dict):
            raise ValueError("Unexpected conversation structure: Error: conversation field is not a dict")

        # collect all session indices present under conv
        # session_indices = set()
        # for k in conv.keys():
        #     m1 = session_key_re.match(k)
        #     m2 = dt_key_re.match(k)
        #     if m1:
        #         session_indices.add(int(m1.group(1)))
        #     if m2:
        #         session_indices.add(int(m2.group(1)))

        # if not session_indices:
        #     raise ValueError(f"No session data found in conversation: {rec}")

        # ordered = sorted(session_indices)

        sessions = []
        timestamps = []
        i = 1
        while True:
            session = conv.get(f"session_{i}")
            dt = conv.get(f"session_{i}_date_time")
            if session is None:
                break
            sessions.append(session)
            timestamps.append(datetime.strptime(dt, TS_FMT))
            i += 1

        # timestamps = [datetime.strptime(conv.get(f"session_{i}_date_time"), TS_FMT) for i in ordered]
        # sessions   = [conv.get(f"session_{i}", []) for i in ordered]

        conversations.append({
            "timestamps": timestamps,
            "sessions": sessions,
        })

    return qas, conversations

def load_locomo10(
        path: str,
        randomize: bool = True
    ) -> Tuple[List[List[Dict[str, Any]]], List[Tuple[datetime, int, str]], List[Dict[str, str]]]:
    """Load LoCoMo10 dataset from JSON file. Flatten conversations into text blocks."""
    qa, conversations = load_locomo10_raw(path)

    session_id = 1

    conv_list = []
    evidence_id_maps: List[Dict[str, str]] = []
    for c in conversations:
        timestamps = c["timestamps"]
        sessions = c["sessions"]
        id_map = {}
        for ts, session in zip(timestamps, sessions):
            if timestamps is None or len(session) == 0:
                continue

            full_text = ""
            for turn in session:
                speaker = turn["speaker"]
                text = turn["text"]
                full_text += f"{speaker}: {text}\n"
                id_map[turn["dia_id"]] = f"{speaker}: {text}"
            if randomize:
                insert_index = random.randrange(len(conv_list) + 1)  # 0..len inclusive
                conv_list.insert(insert_index, (ts, session_id, full_text))
            else:
                conv_list.append((ts, session_id, full_text))
        session_id += 1
        evidence_id_maps.append(id_map)
    return qa, conv_list, evidence_id_maps
    

store = None
embedder = None
async def init():
    global store
    global embedder

    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:9999",
        auth=(
            "neo4j",
            "password",
        ),
    )

    store = Neo4jVectorGraphStore(
        Neo4jVectorGraphStoreParams(
            driver=driver,
            max_concurrent_transactions=200,
            force_exact_similarity_search=False,
        )
    )

    embedder = OpenAIEmbedder(
        {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    await store.create_fulltext_index()

async def add_episode_bulk(episodes):
    global start
    global store
    global embedder

    language_model = OpenAILanguageModel(
        {
            "model": "gpt-5-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    node_map = {}
    node_related_episode_map: DefaultDict[str, set[UUID]] = defaultdict(set)
    edge_map = {}
    episode_edge_map = {}
    nodes = []
    edges = []
    episode_edges = []

    if store is None or embedder is None:
        await init()

    async def generate_edges_nodes(episode, source, relation, target):
        triple_text = f"{source} {relation} {target}"
        if target == "":
            target = source

        try:
            hybrid_search_source = await store.hybrid_search_nodes(
                node_name=source,
                rrf_weights=[0, 1], # Only exact match or substring match
                limit=None,
                required_properties={"session_id": episode.properties["session_id"]},
            )
        except Exception as e:
            print(f"Error during hybrid search for source node '{source}', triple:{triple_text}: {str(e)}")
            raise

        try:
            hybrid_search_target = await store.hybrid_search_nodes(
                node_name=target,
                rrf_weights=[0, 1], # Only exact match or substring match
                limit=None,
                required_properties={"session_id": episode.properties["session_id"]},
            )
        except Exception as e:
            print(f"Error during hybrid search for target node '{target}', triple:{triple_text}: {str(e)}")
            raise

        async def refer_same_entity(content1: str, content2: str, entity_name: str) -> bool:
            # q_prompt = f"ENTITY: {entity_name}\nCONTENT1: {content1}\nCONTENT2: {content2}\n"
            # response_text, _ = await language_model.generate_response(
            #     system_prompt=
            #     """
            #     Given CONTENT1, CONTENT2, and ENTITY. Determine if ENTITY in CONTENT1 and CONTENT2 refer to the same real-world entity.
            #     Answer with "YES" or "NO" only. If uncertain, answer "NO".
            #     """,
            #     user_prompt=q_prompt,
            # )
            # return response_text.strip().upper() == "YES"
            return True
        
        async def get_related_episodes(uuid, session_id) -> set[Node]:
            return await store.search_related_nodes(
                node_uuid=uuid,
                allowed_relations=["MENTIONS"],
                find_sources=True,
                find_targets=False,
                limit=None,
                required_labels=["Episode"],
                required_properties={"session_id": session_id},
            )

        source_related_episodes = None
        target_related_episodes = None
        
        # TODO: currently assume source/target entity in same batch of episodes are the same
        if source not in node_map:
            # TODO: Optimize by batch processing with asyncio.gather
            for n in hybrid_search_source:
                if source == n.properties["name"]:
                    result_episodes = await get_related_episodes(n.uuid, episode.properties["session_id"])
                    if len(result_episodes) == 0:
                        continue
                    if await refer_same_entity(episode.properties["content"], "\n".join([e.properties["content"] for e in result_episodes]), source):
                        node_map[source] = n.uuid
                        source_related_episodes = result_episodes
                        # print(f"Source {source} found in KG referring same entity. Current entity:\n{episode.properties['content']}\nRelated episodes:\n" + "\n".join([e.properties["content"] for e in result_episodes]))
                        break
        
        if target not in node_map:
            for n in hybrid_search_target:
                if target == n.properties["name"]:
                    result_episodes = await get_related_episodes(n.uuid, episode.properties["session_id"])
                    if len(result_episodes) == 0:
                        continue
                    if await refer_same_entity(episode.properties["content"], "\n".join([e.properties["content"] for e in result_episodes]), target):
                        node_map[target] = n.uuid
                        target_related_episodes = result_episodes
                        # print(f"Target {target} found in KG referring same entity. Current entity:\n{episode.properties['content']}\nRelated episodes:\n" + "\n".join([e.properties["content"] for e in result_episodes]))
                        break
        
        if source not in node_map:
            node = Node(
                uuid=uuid4(),
                labels={"Entity"},
                properties={"name": source, "session_id": episode.properties["session_id"]},
            )
            nodes.append(node)
            node_map[source] = node.uuid
            node_related_episode_map[source].add(episode.uuid)
            # print(f"Created source node: {source} with UUID {source_node.uuid}")
        
        if target not in node_map:
            node = Node(
                uuid=uuid4(),
                labels={"Entity"},
                properties={"name": target, "session_id": episode.properties["session_id"]}
            )
            nodes.append(node)
            node_map[target] = node.uuid
            node_related_episode_map[target].add(episode.uuid)
            # print(f"Created target node: {target} with UUID {target_node.uuid}")

        # Add edge to list first, check existence later after got embedded_triple_text
        if triple_text not in edge_map:
            edge = Edge(
                uuid=uuid4(),
                source_uuid=node_map[source],
                target_uuid=node_map[target],
                relation="RELATED_TO",
                properties={"relation": relation, "triple_text": triple_text, "session_id": episode.properties["session_id"]},
            )
            edges.append(edge)
            # print(f"Added edge: {triple_text} with UUID {edges[-1].uuid}")
            edge_map[triple_text] = edge

        # TODO: Optimize by batch processing with asyncio.gather
        if source_related_episodes is None:
            source_related_episodes = await get_related_episodes(node_map[source], episode.properties["session_id"])

        if target_related_episodes is None:
            target_related_episodes = await get_related_episodes(node_map[target], episode.properties["session_id"])

        # Add episode edges
        related_episodes_uuid: set[UUID] = set()
        related_episodes_uuid.update([e.uuid for e in source_related_episodes])
        related_episodes_uuid.update([e.uuid for e in target_related_episodes])
        related_episodes_uuid.update(node_related_episode_map[source])
        related_episodes_uuid.update(node_related_episode_map[target])

        e_to_source_id = str(episode.uuid) + "-" + str(node_map[source])
        if e_to_source_id not in episode_edge_map:
            # Add edge from episode to source node
            episode_edges.append(
                Edge(
                    uuid=uuid4(),
                    source_uuid=episode.uuid,
                    target_uuid=node_map[source],
                    relation="MENTIONS",
                    properties={"mention_by": triple_text, "session_id": episode.properties["session_id"]},
                )
            )
            episode_edge_map[e_to_source_id] = True

        e_to_target_id = str(episode.uuid) + "-" + str(node_map[target])
        if e_to_target_id not in episode_edge_map:
            # Add edge from episode to target node
            episode_edges.append(
                Edge(
                    uuid=uuid4(),
                    source_uuid=episode.uuid,
                    target_uuid=node_map[target],
                    relation="MENTIONS",
                    properties={"mention_by": triple_text, "session_id": episode.properties["session_id"]},
                )
            )
            episode_edge_map[e_to_target_id] = True
        
        # Create edges from current episode to the episodes related to source node
        for uuid in related_episodes_uuid:
            if uuid == episode.uuid:
                continue

            key = str(episode.uuid) + "-" + str(uuid)
            if key in episode_edge_map:
                continue
            
            episode_edges.append(
                Edge(
                    uuid=uuid4(),
                    source_uuid=episode.uuid,
                    target_uuid=uuid,
                    relation="MENTIONS",
                    properties={"session_id": episode.properties["session_id"]},
                )
            )
            episode_edge_map[key] = True

    tasks = [asyncio.create_task(extract_dialogue_relations(e.properties["content"])) for e in episodes]

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Start relation extraciton on {len(episodes)} episodes")
    
    relations = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Finished relation extraction, got {len(relations)} relations. Start generating nodes and edges")

    for triples, e in zip(relations, episodes):
        # print(f"Episode content:\n{e.properties['content']}\nExtracted triples:")
        for s, r, o in triples:
            # print(f"  ({s})-[{r}]->({o})")
            source = s
            target = o
            relation = r

            if target is None:
                target = ""

            if type(target) == list:
                for t in target:
                    await generate_edges_nodes(e, source, relation, t)
            elif type(target) == str:
                await generate_edges_nodes(e, source, relation, target)
            else:
                raise Exception(f"Unknown target type in relation triple: {type(target)}")
        
    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Finished generating {len(nodes)} nodes and {len(edges)} edges and {len(episode_edges)} episode edges, start bulk embedding")

    # Bulk embed edges
    # elapsed = time.perf_counter() - start
    # print(f"({elapsed:.3f}s) Starting bulk embeddings {len(edges)} edges")

    if len(edges) == 0 or len(nodes) == 0:
        print(f"Episode {episodes[0].properties['content']} generated zero nodes or edges. Relations: {relations}. Skip adding.")
        return

    num_batch = 500
    if len(edges) < num_batch:
        num_batch = len(edges) if len(edges) > 0 else 1
    embeddings = []
    for j in range(0, len(edges), num_batch):
        if j + num_batch > len(edges):
            num_batch = len(edges) - j
        batch = [t.properties["triple_text"] for t in edges[j:j+num_batch]]
        batch_embeddings = await embedder.ingest_embed(batch)
        embeddings.extend(batch_embeddings)

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Finished bulk embeddings. Start dedup {len(edges)} edges")

    deduped_edges = []
    for edge, embedding in zip(edges, embeddings):
        edge.properties["embedding"] = embedding
        # hybrid_search_edge = await store.hybrid_search_edges(
        #     query_text=edge.properties["triple_text"],
        #     query_embedding=edge.properties["embedding"],
        #     limit=1,
        # )
        # if len(hybrid_search_edge) != 0 and hybrid_search_edge[0].properties["triple_text"] == edge.properties["triple_text"]:
        #     continue
        deduped_edges.append(edge)
    
    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Finished dedup. Start adding {len(nodes)} nodes, {len(edges)} edges(deduped from {len(edges)}), {len(episode_edges)} episode edges, {len(episodes)} episodes to graph")
    await store.add_nodes(episodes)
    await store.add_nodes(nodes)
    await store.add_edges(episode_edges)
    await store.add_edges(edges)

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Finished bulk adding episodes, nodes, edges")

num_test_cases = 200

async def generate_kg_wikimultihop():
    global start
    global num_test_cases
    global starting_test_case

    episodes = []
    questions = []
    answers = []
    added_contexts = set()

    contexts, questions, answers = load_data(start_line=1, num_cases=num_test_cases, randomize=True)

    print("Loaded", len(contexts), "contexts, start generating KG")
    t1 = datetime.now(timezone.utc)
    for i in range(len(contexts)):
        # The dataset may contain duplicate contexts
        if contexts[i] not in added_contexts:
            episodes.append(Node(
                uuid=uuid4(),
                labels={"Episode"},
                # Make timestamp different for each episode
                properties={"content": contexts[i], "timestamp": t1 + timedelta(seconds=i), "session_id": 1},
            ))
            added_contexts.add(contexts[i])
        
        n_batch = 100
        if (i + 1) % n_batch == 0 or i == len(contexts) - 1:
            elapsed = time.perf_counter() - start
            print(f"({elapsed:.3f}s) Start bulk adding {i - n_batch + 1} - {i} episodes =====")
            
            await add_episode_bulk(episodes)
            episodes = []

            elapsed = time.perf_counter() - start
            print(f"({elapsed:.3f}s) Finished bulk adding {i} - {min(i+n_batch, len(contexts))} episodes =====")

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Completed generating KG")

async def search_kg(query: str, session_id: int, limit: int = 50) -> tuple[list[str], list[Node]]:
    global start

    st = time.perf_counter()
    print(f"Searching KG for query: {query} with session_id: {session_id}")

    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:9999",
        auth=(
            "neo4j",
            "password",
        ),
    )

    store = Neo4jVectorGraphStore(
        Neo4jVectorGraphStoreParams(
            driver=driver,
            max_concurrent_transactions=200,
            force_exact_similarity_search=False,
        )
    )

    embedder = OpenAIEmbedder(
        {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    await store.create_fulltext_index()

    q_embedding = (await embedder.search_embed([query]))[0]

    hybrid_search_edges = await store.search_similar_edges(
        query_text=query,
        query_embedding=q_embedding,
        limit=10,
        allowed_relations=["RELATED_TO"],
        required_properties={"session_id": session_id},
    )

    entities = extract_entities(query, "")
    print(f"Extracted entities from query: {entities}")

    hybrid_search_nodes = []
    for ent in entities:
        hybrid_search_nodes.extend(
            await store.hybrid_search_nodes(
                node_name=ent,
                rrf_weights=[0.4,0.6],
                limit=10,
                required_properties={"session_id": session_id},
            )
        )

    triple_texts = [
        e.properties["triple_text"]
        for e in hybrid_search_edges
    ]

    # print("Found edges: ", "\n".join(triple_texts))

    uuids = set()
    for s in hybrid_search_edges:
        uuids.add(s.source_uuid)
        uuids.add(s.target_uuid)

    for n in hybrid_search_nodes:
        uuids.add(n.uuid)

    related_episodes = {}
    # Get episodes related to the entity nodes
    for uuid in uuids:
        result = await store.search_related_nodes(
            node_uuid=uuid,
            allowed_relations=["MENTIONS"],
            find_sources=True,
            find_targets=False,
            limit=None,
            required_labels=["Episode"],
            required_properties={"session_id": session_id},
        )
        for n in result:
            related_episodes[n.uuid] = n
    # print("Found", len(related_episodes), "related episodes")
    
    # 2nd node search based on entities found in related episodes
    episode_contexts = "\n".join([n.properties["content"] for n in related_episodes.values()])
    entities_in_episodes = extract_entities(episode_contexts, query)

    hybrid_search_nodes = []
    for ent in entities_in_episodes:
        hybrid_search_nodes.extend(
            await store.hybrid_search_nodes(
                node_name=ent,
                rrf_weights=[0.4,0.6],
                limit=10,
                required_properties={"session_id": session_id},
            )
        )
    
    uuids_new = set()
    for s in hybrid_search_nodes:
        if s.uuid not in uuids:
            uuids_new.add(s.uuid)
    # print("Found", len(uuids_new), "hybrid search nodes in 2nd round")

    # 2nd round related episodes
    for uuid in uuids_new:
        result = await store.search_related_nodes(
            node_uuid=uuid,
            allowed_relations=["MENTIONS"],
            find_sources=True,
            find_targets=False,
            limit=None,
            required_labels=["Episode"],
            required_properties={"session_id": session_id},
        )
        for n in result:
            if n.uuid not in related_episodes:
                related_episodes[n.uuid] = n

    # pointed_episodes = {}
    # # Get the episodes directly pointed by the result related_episodes
    # for uuid, n in related_episodes.items():
    #     result = await store.search_related_nodes(
    #         node_uuid=uuid,
    #         allowed_relations=["MENTIONS"],
    #         find_sources=True,
    #         find_targets=False,
    #         limit=None,
    #         required_labels=["Episode"],
    #     )
    #     for n in result:
    #         pointed_episodes[n.uuid] = n
    
    # related_episodes.update(pointed_episodes)

    # print("Found total", len(related_episodes), "related episodes after 2nd round")

    related_episodes_sorted = sorted(
        list(related_episodes.values()),
        key=lambda e: (e.properties.get('timestamp') is None,
                    e.properties.get('timestamp'))
    )

    print(f"Search KG for query: {query} took {time.perf_counter() - st:.3f}s, found {len(triple_texts)} triples, {len(related_episodes_sorted)} related episodes")

    return triple_texts[:limit], related_episodes_sorted[-limit:]

async def wikimultihop_accuracy():
    global num_test_cases
    global starting_test_case
    global filtered_dataset_path

    language_model = OpenAILanguageModel(
        {
            "model": "gpt-5-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    verify_model = OpenAILanguageModel(
        {
            "model": "gpt-4.1",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    questions = []
    answers = []
    total_processed = 0
    total_score = 0.0

    # Prepare questions in batches
    num_parallel = 40
    q_batchs = []
    q_batch = []
    with open(filtered_dataset_path, "r", encoding="utf-8") as f:
        l = 0
        print("Loading questions and answers...")
        for line in f:
            # if l < starting_test_case:
            #     l += 1
            #     continue
            if l > num_test_cases:
                break
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            q_batch.append(
                {
                    "question": obj["question"],
                    "answer": str(obj["answer"]),
                    "session_id": 1, # Use same session id for wikimultihop dataset
                }
            )
            if len(q_batch) >= num_parallel:
                q_batchs.append(q_batch)
                q_batch = []
            l += 1
    if len(q_batch) > 0:
        q_batchs.append(q_batch)

    # Parallel generate and verify answers
    for q_batch in q_batchs:
        r_batch = []
        search_tasks = []

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Starting parallel search on KG for {len(q_batch)} questions...")

        for qa in q_batch:
            search_tasks.append(search_kg(qa["question"], qa["session_id"]))
            if qa["question"] == "":
                raise Exception("Empty question found in batch")
            if qa["answer"] == "":
                raise Exception("Empty answer found in batch")
            if qa["session_id"] <= 0:
                raise Exception("Invalid session_id found in batch")
            r_batch.append({
                "question": qa["question"],
                "answer": qa["answer"],
                "session_id": qa["session_id"],
            })
        search_result = await asyncio.gather(*search_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel search on KG for {len(q_batch)} questions. Starting to generate answers in parallel...")

        response_tasks = []
        for (triple_texts, episodes), r in zip(search_result, r_batch):
            content = ""
            for e in episodes:
                content += e.properties["timestamp"].strftime("%Y-%m-%d %H:%M:%S") + "\n"
                content += e.properties["content"] + "\n"

            # TODO: Extract the join operation outside the f-string
            triple_texts_joined = '\n'.join(triple_texts)
            
            r["triple_texts_joined"] = triple_texts_joined
            r["episodes"] = episodes
            r["content"] = content
            
            q_prompt = f"RELATION_TRIPPLES:\n{triple_texts_joined}\nCONTEXT:\n{content}\nQUERY: {r["question"]}"
            s_prompt="""
            Given the following RELATION_TRIPPLES between entities and CONTEXT, answer the QUERY.
            Guidlines:
                - Give the answer based on the provided information only.
                - Do not user any external knowledge or lookup
                - If cannot determine, include 'Cannot determine' in the response.
            """

            response_tasks.append(language_model.generate_response(
                system_prompt=s_prompt,
                user_prompt=q_prompt,
            ))
        
        response_results = await asyncio.gather(*response_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel answer genereation for {len(q_batch)} questions. Starting to validate answers in parallel...")

        for (response_text, _), r in zip(response_results, r_batch):
            r["response_text"] = response_text

        async def validate_answer(response_text: str, answer: str):
            fail_text = "Cannot determine"
            rfold = response_text.casefold()
            afold = answer.casefold()
            if rfold == afold:
                score = 1
            elif fail_text.casefold() in rfold:
                score = 0
            elif afold in rfold:
                score = 1
            else:
                valid_text, _ = await verify_model.generate_response(
                    system_prompt=
                    """
                    Given the RESPONSE and ANSWER, determine if the RESPONSE has the same meaning as ANSWER.
                    Do not user any external knowledge or lookup.
                    If they meant the similar or same, return 1. It the RESPONSE contains partial answer,
                    return 0.5, otherwise return 0. Only return the number 1, 0.5 or 0.
                    """,
                    user_prompt=f"RESPONSE: {response_text}\nANSWER:{answer}",
                )
                try:
                    score = float(valid_text.strip())
                except:
                    print("Failed to parse score:", valid_text)
                    score = 0
            return score
        
        # Validate answers in parallel
        validate_tasks = [validate_answer(r["response_text"], r["answer"]) for r in r_batch]
        validate_results = await asyncio.gather(*validate_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel validating answers for {len(q_batch)} questions...")

        for r, score in zip(r_batch, validate_results):
            r["score"] = score
        
        # Print batch results
        for r in r_batch:
            total_processed += 1
            total_score += r["score"]
            
            if r["score"] != 1:
                c = ""
                for e in r["episodes"]:
                    if e.properties["session_id"] != r["session_id"]:
                        print(f"Warning: Returned episode session_id {e.properties['session_id']} does not match question session_id {r['session_id']}")
                        print(f"Episode content:\n{e.properties['content'][:50]}...\n")
                    c += e.properties["timestamp"].strftime("%Y-%m-%d %H:%M:%S") + "\n"
                    c += f"Session ID: {e.properties["session_id"]}\n"
                    c += e.properties["content"][:30] + "...\n"
                print(f"For question:\n{r["question"]}\nSearch result content:\n{c}\n")
            
            print(f"Q: {r["question"]}\nA: {r["answer"]}\nR: {r["response_text"]}\nScore: {r["score"]}")
            print(f"Current Answer Accuracy: {total_score}/{total_processed}({total_score / total_processed:.3f})")
            print(f"KG search returned {len(r["episodes"])} episodes.\n---\n")

async def filter_wikimultihop_dataset_questions():
    global filtered_dataset_path
    language_model = OpenAILanguageModel(
        {
            "model": "gpt-5-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    verify_model = OpenAILanguageModel(
        {
            "model": "gpt-4.1",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    total_processed = 0
    total_score = 0

    start = time.perf_counter()
    with open("/home/tomz/graphiti/data/dev.json", "r", encoding="utf-8") as f:
        i = 1
        for line in f:
            # if i <= starting_test_case:
            #     i += 1
            #     continue
            if i > num_test_cases:
                break

            cur_line = line.strip()
            if not cur_line:
                continue
            obj = json.loads(cur_line)
            obj["context"] = json.loads(obj["context"])
            context_str = ""
            for key, sentences in obj["context"]:
                context_str += f"{key}:\n"
                for s in sentences:
                    context_str += s + "\n"
            
            elapsed = time.perf_counter() - start
            print(f"[#{i}]({elapsed:.3f}s) Generating answer.")
            
            q_prompt = f"CONTEXT:\n{context_str}\nQUESTION: {obj['question']}"
            response_text, _ = await language_model.generate_response(
                system_prompt="Given the following CONTEXT, answer the question. Do not user any external knowledge or lookup. If cannot determine, include 'Cannot determine' in the response.",
                user_prompt=q_prompt,
            )

            elapsed = time.perf_counter() - start
            print(f"[#{i}]({elapsed:.3f}s) Answer generated. Starting to validate the answer...")

            valid_text, _ = await verify_model.generate_response(
                system_prompt="Given the response and correct answer, judge if the response is the correct answer. If it is correct, return 1, otherwise return 0.",
                user_prompt=f"Response: {response_text}\nAnswer:{obj['answer']}",
            )

            fail_text = "Cannot determine"
            rfold = response_text.casefold()
            afold = obj['answer'].casefold()
            if rfold == afold:
                score = 1
            elif fail_text.casefold() in rfold:
                score = 0
            elif afold in rfold:
                score = 1
            else:
                valid_text, _ = await language_model.generate_response(
                    system_prompt="Given the RESPONSE and ANSWER, determine if the RESPONSE has the same meaning as ANSWER. If they meant the same, return 1, otherwise return 0.",
                    user_prompt=f"RESPONSE: {response_text}\nANSWER:{obj['answer']}",
                )
                try:
                    score = float(valid_text.strip())
                except:
                    print("Fqqailed to parse score:", valid_text)
                    continue

            total_processed += 1
            total_score += score
            
            print(f"[#{i}]({elapsed:.3f}s) Q: {obj['question']}\nA: {obj['answer']}\nR: {response_text}\nS: {score}, {total_score}/{total_processed}({total_score / total_processed:.3f})\n")
            if score == 1:
                # Dump the line to a new file
                with open(filtered_dataset_path, "a", encoding="utf-8") as fout:
                    if line[-1] != "\n":
                        line += "\n"
                    fout.write(line)
                    os.fsync(fout.fileno())
            i += 1

async def filter_locomo_dataset_questions():
    global locomo_path
    global filtered_locomo_qa_path
    language_model = OpenAILanguageModel(
        {
            "model": "gpt-5-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    verify_model = OpenAILanguageModel(
        {
            "model": "gpt-4.1",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    total_processed = 0
    total_score = 0

    start = time.perf_counter()
    qas, conversations = load_locomo10_raw(locomo_path)
    for i in range(len(conversations)):
        context = ""
        timestamps = conversations[i]["timestamps"]
        sessions = conversations[i]["sessions"]
        for ts, session in zip(timestamps, sessions):
            if timestamps is None or len(session) == 0:
                continue

            full_text = ""
            for turn in session:
                speaker = turn["speaker"]
                text = turn["text"]
                full_text += f"{speaker}: {text}\n"
            context += f"{ts.strftime('%Y-%m-%d %H:%M:%S')}\n{full_text}\n\n"

        for qa in qas[i]:   
            question = qa["question"]
            answer = str(qa["answer"])
            evicence = qa["evidence"]
            session_id = i + 1

            elapsed = time.perf_counter() - start
            print(f"[#{i}]({elapsed:.3f}s) Generating answer for question: {question}")
            
            q_prompt = f"CONTEXT:\n{context}\nQUESTION: {question}"
            response_text, _ = await language_model.generate_response(
                system_prompt="Given the following CONTEXT, answer the question. Do not user any external knowledge or lookup. Make the answer precise and short. If cannot determine, include 'Cannot determine' in the response.",
                user_prompt=q_prompt,
            )

            elapsed = time.perf_counter() - start
            print(f"[#{i}]({elapsed:.3f}s) Answer generated. Starting to validate the answer...")

            valid_text, _ = await verify_model.generate_response(
                system_prompt="Given the response and correct answer, judge if the response is the correct answer. If it is correct, return 1, otherwise return 0.",
                user_prompt=f"Response: {response_text}\nAnswer:{answer}",
            )

            fail_text = "Cannot determine"
            rfold = response_text.casefold()
            afold = answer.casefold()
            if rfold == afold:
                score = 1
            elif fail_text.casefold() in rfold:
                score = 0
            elif afold in rfold:
                score = 1
            else:
                valid_text, _ = await language_model.generate_response(
                    system_prompt="Given the RESPONSE and ANSWER, determine if the RESPONSE has the same meaning as ANSWER. If they meant the same, return 1, otherwise return 0.",
                    user_prompt=f"RESPONSE: {response_text}\nANSWER:{answer}",
                )
                try:
                    score = float(valid_text.strip())
                except:
                    print("Fqqailed to parse score:", valid_text)
                    continue

            total_processed += 1
            total_score += score
            
            print(f"[#{i}]({elapsed:.3f}s) Q: {question}\nA: {answer}\nR: {response_text}\nS: {score}, {total_score}/{total_processed}({total_score / total_processed:.3f})\n")
            if score == 1:
                with open(filtered_locomo_qa_path, "a", encoding="utf-8") as f:
                    json.dump({"question": question, "answer": answer, "evicence": evicence, "session_id": session_id}, f, ensure_ascii=False)
                    f.write("\n")
            else:
                print("User prompt:\n", q_prompt)

async def generate_kg_locomo():
    global locomo_path
    _, sessions, _ = load_locomo10(locomo_path)
    print("Loaded", len(sessions), "sessions, start generating KG")

    episodes = []
    t1 = datetime.now(timezone.utc)
    for i in range(len(sessions)):
        ts, session_id, session_text = sessions[i]
        episodes.append(Node(
            uuid=uuid4(),
            labels={"Episode"},
            # Make timestamp different for each episode
            properties={"content": session_text, "timestamp": ts, "session_id": session_id}
        ))  
        
        n_batch = 100
        if (i + 1) % n_batch == 0 or i == len(sessions) - 1:
            elapsed = time.perf_counter() - start
            print(f"({elapsed:.3f}s) Start bulk adding {i - n_batch + 1} - {i} episodes =====")
            
            await add_episode_bulk(episodes)
            episodes = []

            elapsed = time.perf_counter() - start
            print(f"({elapsed:.3f}s) Finished bulk adding {i} - {min(i+n_batch, len(sessions))} episodes =====")

    elapsed = time.perf_counter() - start
    print(f"({elapsed:.3f}s) Completed generating KG")

async def locomo_accuracy():
    global locomo_path
    global filtered_locomo_qa_path
    language_model = OpenAILanguageModel(
        {
            "model": "gpt-5-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    verify_model = OpenAILanguageModel(
        {
            "model": "gpt-4.1",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )

    total_processed = 0
    total_score = 0.0
    total_context_score = 0
    total_evidence_processed = 0
    # questions = json.load(open(filtered_locomo_qa_path, "r", encoding="utf-8"))
    qas, _, evidence_id_maps = load_locomo10(locomo_path)

    filtered = []
    with open(filtered_locomo_qa_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            filtered.append(rec["question"])

    # Prepare questions in batches
    num_parallel = 100
    q_batchs = []
    q_batch = []
    for i in range(len(qas)):
        session_id = i + 1
        for j in range(len(qas[i])):
            qa = qas[i][j]
            if qa['question'] not in filtered:
                continue
            
            if "question" not in qa:
                raise Exception("Field 'question' not found in question record")
            if "answer" not in qa:
                raise Exception("Field 'answer' not found in question record")
            if "evidence" not in qa:
                raise Exception("Field 'evidence' not found in question record")

            evidence_strs = []
            for id in qa["evidence"]:
                if id not in evidence_id_maps[i]:
                    print(f"Warning: evidence ID {id} not found in evidence_id_map for session {session_id}")
                    continue
                evidence_strs.append(evidence_id_maps[i][id])

            q_batch.append(
                {
                    "question": qa["question"],
                    "answer": str(qa["answer"]),
                    "evidence": qa["evidence"],
                    "session_id": session_id,
                    "evidence_strs": evidence_strs,
                }
            )
            if len(q_batch) >= num_parallel:
                q_batchs.append(q_batch)
                q_batch = []
    if len(q_batch) > 0:
        q_batchs.append(q_batch)


    # Parallel generate and verify answers
    for q_batch in q_batchs:
        r_batch = []
        search_tasks = []

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Starting parallel search on KG for {len(q_batch)} questions...")

        for qa in q_batch:
            search_tasks.append(search_kg(qa["question"], qa["session_id"]))
            if qa["question"] == "":
                raise Exception("Empty question found in batch")
            if qa["answer"] == "":
                raise Exception("Empty answer found in batch")
            if "evidence" not in qa:
                raise Exception("Missing field evidence in batch")
            if qa["session_id"] <= 0:
                raise Exception("Invalid session_id found in batch")
            r_batch.append({
                "question": qa["question"],
                "answer": qa["answer"],
                "evidence": qa["evidence"],
                "session_id": qa["session_id"],
                "evidence_strs": qa["evidence_strs"],
            })
        search_result = await asyncio.gather(*search_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel search on KG for {len(q_batch)} questions. Starting to generate answers in parallel...")

        response_tasks = []
        for (triple_texts, episodes), r in zip(search_result, r_batch):
            content = ""
            for e in episodes:
                content += e.properties["timestamp"].strftime("%Y-%m-%d %H:%M:%S") + "\n"
                content += e.properties["content"] + "\n"

            # TODO: Extract the join operation outside the f-string
            triple_texts_joined = '\n'.join(triple_texts)
            
            r["triple_texts_joined"] = triple_texts_joined
            r["episodes"] = episodes
            r["content"] = content
            
            q_prompt = f"RELATION_TRIPPLES:\n{triple_texts_joined}\nCONTEXT:\n{content}\nQUERY: {r["question"]}"
            s_prompt="""
            Given the following RELATION_TRIPPLES between entities and CONTEXT, answer the QUERY.
            Guidlines:
                - Give the answer based on the provided information only.
                - Given RELATION_TRIPPLES and CONTEXT may contains noisy or irrelevant information.
                Try to find the information relevant to QUERY first. Then use only those relevant
                information to andswer the QUERY.
                - If cannot determine, include 'Cannot determine' in the response.
            """

            response_tasks.append(language_model.generate_response(
                system_prompt=s_prompt,
                user_prompt=q_prompt,
            ))
        
        response_results = await asyncio.gather(*response_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel answer genereation for {len(q_batch)} questions. Starting to validate answers in parallel...")

        for (response_text, _), r in zip(response_results, r_batch):
            r["response_text"] = response_text

        async def validate_answer(response_text: str, answer: str):
            fail_text = "Cannot determine"
            rfold = response_text.casefold()
            afold = answer.casefold()
            if rfold == afold:
                score = 1
            elif fail_text.casefold() in rfold:
                score = 0
            elif afold in rfold:
                score = 1
            else:
                valid_text, _ = await verify_model.generate_response(
                    system_prompt=
                    """
                    Given the RESPONSE and ANSWER, determine if the RESPONSE has the same meaning as ANSWER.
                    Do not user any external knowledge or lookup.
                    If they meant the similar or same, return 1. It the RESPONSE contains partial answer,
                    return 0.5, otherwise return 0. Only return the number 1, 0.5 or 0.
                    """,
                    user_prompt=f"RESPONSE: {response_text}\nANSWER:{answer}",
                )
                try:
                    score = float(valid_text.strip())
                except:
                    print("Failed to parse score:", valid_text)
                    score = 0
            return score
        
        # Validate answers in parallel
        validate_tasks = [validate_answer(r["response_text"], r["answer"]) for r in r_batch]
        validate_results = await asyncio.gather(*validate_tasks)

        elapsed = time.perf_counter() - start
        print(f"({elapsed:.3f}s) Finished parallel validating answers for {len(q_batch)} questions...")

        for r, score in zip(r_batch, validate_results):
            r["score"] = score

            context_score = 1
            missing_evidence_str = ""
            for s in r["evidence_strs"]:
                if (s not in r["content"]) and (s not in r["triple_texts_joined"]):
                    context_score = 0
                    missing_evidence_str += f"{id}: {s}\n"
                    print(f"Missing evidence ID {id}, text: {s} text in retrieved content/triples:\n{r["content"]}")
            r["missing_evidence_str"] = missing_evidence_str
            r["context_score"] = context_score
        
        # Print batch results
        for r in r_batch:
            total_processed += 1
            total_score += r["score"]

            if len(r["evidence"]) > 0:
                total_context_score += r["context_score"]
                total_evidence_processed += 1
            
            if r["score"] != 1:
                c = ""
                for e in r["episodes"]:
                    if e.properties["session_id"] != r["session_id"]:
                        print(f"Warning: Returned episode session_id {e.properties['session_id']} does not match question session_id {r['session_id']}")
                        print(f"Episode content:\n{e.properties['content'][:50]}...\n")
                    c += e.properties["timestamp"].strftime("%Y-%m-%d %H:%M:%S") + "\n"
                    c += f"Session ID: {e.properties["session_id"]}\n"
                    c += e.properties["content"][:30] + "...\n"
                print(f"For question:\n{r["question"]}\nSearch result content:\n{c}\n")
            
            print(f"Q: {r["question"]}\nA: {r["answer"]}\nR: {r["response_text"]}\nScore: {r["score"]}\nContext Score: {r["context_score"]}")
            print(f"Current Answer Accuracy: {total_score}/{total_processed}({total_score / total_processed:.3f})")
            print(f"Evidences:\n{r["evidence_strs"]}")
            if r["context_score"] == 0:
                print(f"Missing Evidences:\n{r["missing_evidence_str"]}\n")
            print(f"Current Context Accuracy: {total_context_score}/{total_evidence_processed}({total_context_score / total_evidence_processed:.3f})")
            print(f"KG search returned {len(r["episodes"])} episodes.\n---\n")

def main():
    """Main function"""
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ No OpenAI API key found!")
        print("Please set: export OPENAI_API_KEY='your-key-here'")
        return

    init_dspy()
    
    print(f"Running dialogue relation extraction tests with {model}, answering model GPT-5-Nano...")
    # asyncio.run(filter_locomo_dataset_questions())
    # asyncio.run(generate_kg_wikimultihop())
    asyncio.run(wikimultihop_accuracy())
    # asyncio.run(generate_kg_locomo())
    # asyncio.run(locomo_accuracy())

if __name__ == "__main__":
    main()
