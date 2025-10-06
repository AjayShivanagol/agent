from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from typing import Any, List, Dict
import pandas as pd
import os
from contextlib import asynccontextmanager
import re

# Faiss and Sentence-Transformers imports
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import torch # For converting embeddings to numpy if using GPU

# Global variables
costing_df: pd.DataFrame = pd.DataFrame()
embedding_model = None # Global variable for the SentenceTransformer model
faiss_index = None     # Global variable for the Faiss index

# Define Pydantic models
class SearchRequest(BaseModel):
    query_term: str
    limit: int | None = 10
    offset: int | None = 0

class CoCostingItemView(BaseModel):
    itemNo: str | None = None
    material: str | None = None
    currency: str | None = None
    price: float | None = None
    quantity: int | None = None
    action: str | None = None
    activityType: str | None = None
    baseUnit: str | None = None
    businessArea: str | None = None
    componentId: str | None = None
    costCenter: str | None = None
    costElement: str | None = None
    costEstNo: str | None = None
    costingDate: str | None = None
    costingType: str | None = None
    costingVersion: str | None = None
    currencyTypeCode: str | None = None
    errMsg: str | None = None
    fixValue: float | None = None
    fixedValue: float | None = None
    itemCategory: str | None = None
    ledger: str | None = None
    materialCompositeKey: str | None = None
    materialDesc: str | None = None
    materialSpecProcTypeCosting: str | None = None
    mixedCosting: str | None = None
    mixingRatio: float | None = None
    operation: str | None = None
    parentMaterial: str | None = None
    parentMaterialCompositeKey: str | None = None
    parentMaterialSpecProcTypeCosting: str | None = None
    parentPlant: str | None = None
    plant: str | None = None
    priceUnit: float | None = None
    processCategory: str | None = None
    procurementAlternative: str | None = None
    profitCenter: str | None = None
    purcDocNum: str | None = None
    purcItemNo: str | None = None
    referenceObject: str | None = None
    selectionIdType: str | None = None
    srcSys: str | None = None
    supplier: str | None = None
    totalValue: float | None = None
    tranSelectionId: str | None = None
    transfCostEstNo: str | None = None
    transfCostingDate: str | None = None
    transfCostingType: str | None = None
    transfCostingVersion: str | None = None
    transfValuationVariant: str | None = None
    transferStrategy: str | None = None
    valuationStrategy: str | None = None
    valuationVariant: str | None = None
    workCenter: str | None = None
    _reportType_csv: str | None = None # Internal field for debugging/verification

class SearchResultResponse(BaseModel):
    code: int
    data: List[CoCostingItemView] | None = None
    totalCount: int | None = None
    message: str | None = None

# Data loading function
def load_costing_data_from_csv():
    """
    Loads costing data from a CSV file into a pandas DataFrame and
    creates a Faiss index from material descriptions.
    """
    global costing_df, embedding_model, faiss_index
    csv_file_path = os.path.join(os.path.dirname(__file__), "costing_data.csv")
    try:
        costing_df = pd.read_csv(csv_file_path, dtype=str)
        costing_df = costing_df.fillna('')

        # Strip whitespace from relevant string columns
        for col in ['material', 'currency', 'reportType', 'materialDesc', 'itemNo', 'supplier', 'componentId', 'businessArea', 'costCenter', 'costElement', 'itemCategory', 'ledger', 'operation', 'parentMaterial', 'plant', 'processCategory', 'profitCenter', 'referenceObject', 'srcSys', 'workCenter']:
            if col in costing_df.columns:
                costing_df[col] = costing_df[col].str.strip()

        # Convert numeric columns
        numeric_cols = ['price', 'quantity', 'fixValue', 'fixedValue', 'mixingRatio', 'priceUnit', 'totalValue']
        for col in numeric_cols:
            if col in costing_df.columns:
                costing_df[col] = pd.to_numeric(costing_df[col], errors='coerce').fillna(0)
            else:
                costing_df[col] = 0.0

        print(f"Successfully loaded data from {csv_file_path}. Rows: {len(costing_df)}")

        # Initialize SentenceTransformer model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("SentenceTransformer model 'all-MiniLM-L6-v2' loaded.")

        # Generate embeddings for material descriptions
        material_descs = costing_df['materialDesc'].fillna('').tolist()
        if not material_descs:
            print("No material descriptions found for embedding. Faiss index will be empty.")
            faiss_index = None
        else:
            embeddings = embedding_model.encode(material_descs, convert_to_tensor=True)
            embeddings_np = embeddings.cpu().numpy().astype('float32')

            # Create Faiss index
            dimension = embeddings_np.shape[1]
            faiss_index = faiss.IndexFlatL2(dimension)
            faiss_index.add(embeddings_np)
            print(f"Faiss index created with {faiss_index.ntotal} vectors of dimension {dimension}.")

        print("\n--- Unique material descriptions (cleaned and lowercased) in DataFrame after loading ---")
        print(costing_df['materialDesc'].str.lower().unique())
        print("--------------------------------------------------------------------------\n")

    except FileNotFoundError:
        print(f"Error: costing_data.csv not found at {csv_file_path}. Please create the file.")
        costing_df = pd.DataFrame(columns=[field.name for field in CoCostingItemView.model_fields.values()] + ['reportType'])
        for col in costing_df.columns:
            if col in ['price', 'quantity', 'fixValue', 'fixedValue', 'mixingRatio', 'priceUnit', 'totalValue']:
                costing_df[col] = 0.0
            else:
                costing_df[col] = ''
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        costing_df = pd.DataFrame(columns=[field.name for field in CoCostingItemView.model_fields.values()] + ['reportType'])
        for col in costing_df.columns:
            if col in ['price', 'quantity', 'fixValue', 'fixedValue', 'mixingRatio', 'priceUnit', 'totalValue']:
                costing_df[col] = 0.0
            else:
                costing_df[col] = ''

# Define lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    Loads data from CSV and creates Faiss index on startup.
    """
    print("Application startup: Loading costing data and initializing Faiss...")
    load_costing_data_from_csv()
    yield
    print("Application shutdown: Cleaning up (if any)...")
    # Add any cleanup code here if necessary

# Pass lifespan to FastAPI app
app = FastAPI(lifespan=lifespan)


# Helper function for keyword and substring search
def _perform_keyword_search_internal(df: pd.DataFrame, search_term: str) -> pd.DataFrame:
    """
    Performs a comprehensive keyword and substring search on the given DataFrame.
    """
    if df.empty or not search_term:
        return pd.DataFrame(columns=df.columns)

    cleaned_search_term_lower = search_term.strip().lower()
    # Simplify the search term by removing content in parentheses for broader matching
    simplified_search_term_lower = re.sub(r'\s*\(.*?\)\s*', '', cleaned_search_term_lower).strip()

    print(f"Performing keyword search across columns for: '{cleaned_search_term_lower}' (simplified: '{simplified_search_term_lower}')")
    
    search_columns = [
        'materialDesc', 'material', 'itemNo', 'supplier', 'currency',
        'businessArea', 'costCenter', 'costElement', 'itemCategory', 
        'ledger', 'operation', 'parentMaterial', 'plant', 
        'processCategory', 'profitCenter', 'referenceObject', 'srcSys', 
        'workCenter'
    ]
    
    combined_match = pd.Series([False] * len(df), index=df.index)

    for col in search_columns:
        if col in df.columns and pd.api.types.is_string_dtype(df[col]):
            # Prioritize exact match
            exact_match = (df[col].str.lower() == cleaned_search_term_lower)
            # Also include substring match using the simplified term
            substring_match = df[col].str.lower().str.contains(simplified_search_term_lower, na=False, regex=False)
            
            col_match = exact_match | substring_match
            combined_match = combined_match | col_match
            
            if col_match.any():
                print(f"  - Found matches in column '{col}'. Total matches so far: {combined_match.sum()}")
        else:
            print(f"  - Skipping column '{col}': Not found or not string dtype.")

    return df[combined_match].copy()

# Helper function for semantic search using Faiss
def _perform_semantic_search_internal(search_term: str, k: int = 10) -> pd.DataFrame:
    """
    Performs semantic search using Faiss for similar items.
    """
    global costing_df, embedding_model, faiss_index

    if embedding_model is None or faiss_index is None:
        print("Embedding model or Faiss index not loaded. Cannot perform semantic search.")
        return pd.DataFrame(columns=costing_df.columns)

    print(f"Performing semantic search using Faiss for: '{search_term}'")
    try:
        query_embedding = embedding_model.encode([search_term.strip().lower()], convert_to_tensor=True)
        query_embedding_np = query_embedding.cpu().numpy().astype('float32')

        # Search across the entire costing_df for similarity
        D, I = faiss_index.search(query_embedding_np, k=k + 1) # Add 1 to k to potentially remove the exact queried item
        
        matched_indices = [idx for idx in I[0] if idx != -1]
        
        if matched_indices:
            faiss_results_df = costing_df.iloc[matched_indices].copy()
            
            # Filter out the exact queried item if it appears in similar results
            final_filtered_df = faiss_results_df[
                faiss_results_df['materialDesc'].str.lower() != search_term.strip().lower()
            ].head(k)
            
            print(f"Faiss found {len(final_filtered_df)} similar matches (excluding exact match).")
            return final_filtered_df
        else:
            print("No similar parts found via Faiss search.")
            return pd.DataFrame(columns=costing_df.columns)
    
    except Exception as e:
        print(f"Error during Faiss search: {e}")
        return pd.DataFrame(columns=costing_df.columns)


@app.post("/integration_layer/resultview/itemView/keywordSearch", response_model=SearchResultResponse)
async def keyword_search_endpoint(request: SearchRequest = Body(...)):
    """
    Endpoint for performing keyword and substring search across costing data.
    Returns a broad set of contextually relevant data.
    """
    global costing_df

    if costing_df.empty:
        raise HTTPException(status_code=500, detail="Costing data not loaded. Check server logs.")

    print(f"\n--- Incoming Keyword Search Request Payload ---")
    print(request.model_dump_json(indent=2))
    print(f"-----------------------------------------------\n")

    filtered_df = _perform_keyword_search_internal(costing_df.copy(), request.query_term)
    
    if filtered_df.empty:
        return SearchResultResponse(code=200, data=[], totalCount=0, message=f"No keyword matches found for '{request.query_term}'.")

    # Apply pagination
    start_index = request.offset if request.offset else 0
    end_index = start_index + request.limit if request.limit else len(filtered_df)
    paginated_df = filtered_df.iloc[start_index:end_index]

    data_items: List[CoCostingItemView] = []
    for _, row in paginated_df.iterrows():
        item_view = CoCostingItemView(
            itemNo=row.get('itemNo'),
            material=row.get('material'),
            currency=row.get('currency'),
            price=row.get('price'),
            quantity=row.get('quantity'),
            supplier=row.get('supplier'),
            materialDesc=row.get('materialDesc'), 
            _reportType_csv=row.get('reportType'), # Include original reportType from CSV
            action=row.get('action'),
            activityType=row.get('activityType'),
            baseUnit=row.get('baseUnit'),
            businessArea=row.get('businessArea'),
            componentId=row.get('componentId'),
            costCenter=row.get('costCenter'),
            costElement=row.get('costElement'),
            costEstNo=row.get('costEstNo'),
            costingDate=row.get('costingDate'),
            costingType=row.get('costingType'),
            costingVersion=row.get('costingVersion'),
            currencyTypeCode=request.query_term, # Pass the query term back for context
            errMsg=row.get('errMsg'),
            fixValue=row.get('fixValue'),
            fixedValue=row.get('fixedValue'),
            itemCategory=row.get('itemCategory'),
            ledger=row.get('ledger'),
            materialCompositeKey=row.get('materialCompositeKey'),
            materialSpecProcTypeCosting=row.get('materialSpecProcTypeCosting'),
            mixedCosting=row.get('mixedCosting'),
            mixingRatio=row.get('mixingRatio'),
            operation=row.get('operation'),
            parentMaterial=row.get('parentMaterial'),
            parentMaterialCompositeKey=row.get('parentMaterialCompositeKey'),
            parentMaterialSpecProcTypeCosting=row.get('parentMaterialSpecProcTypeCosting'),
            parentPlant=row.get('parentPlant'),
            plant=row.get('plant'),
            priceUnit=row.get('priceUnit'),
            processCategory=row.get('processCategory'),
            profitCenter=row.get('profitCenter'),
            purcDocNum=row.get('purcDocNum'),
            purcItemNo=row.get('purcItemNo'),
            referenceObject=row.get('referenceObject'),
            selectionIdType=row.get('selectionIdType'),
            srcSys=row.get('srcSys'),
            totalValue=row.get('totalValue'),
            tranSelectionId=row.get('tranSelectionId'),
            transfCostEstNo=row.get('transfCostEstNo'),
            transfCostingDate=row.get('transfCostingDate'),
            transfCostingType=row.get('transfCostingType'),
            transfCostingVersion=row.get('transfCostingVersion'),
            transfValuationVariant=row.get('transfValuationVariant'),
            transferStrategy=row.get('transferStrategy'),
            valuationStrategy=row.get('valuationStrategy'),
            valuationVariant=row.get('valuationVariant'),
            workCenter=row.get('workCenter')
        )
        data_items.append(item_view)

    return SearchResultResponse(
        code=200,
        data=data_items,
        totalCount=len(filtered_df),
        message=f"Keyword search results for '{request.query_term}'."
    )


@app.post("/integration_layer/resultview/itemView/semanticSearch", response_model=SearchResultResponse)
async def semantic_search_endpoint(request: SearchRequest = Body(...)):
    """
    Endpoint for performing semantic search using Faiss for similar items.
    """
    global costing_df, embedding_model, faiss_index

    if costing_df.empty:
        raise HTTPException(status_code=500, detail="Costing data not loaded. Check server logs.")
    if embedding_model is None or faiss_index is None:
        raise HTTPException(status_code=500, detail="Embedding model or Faiss index not loaded. Cannot perform semantic search.")

    print(f"\n--- Incoming Semantic Search Request Payload ---")
    print(request.model_dump_json(indent=2))
    print(f"---------------------------------------------------\n")

    filtered_df = _perform_semantic_search_internal(request.query_term, k=request.limit if request.limit else 10)

    if filtered_df.empty:
        return SearchResultResponse(code=200, data=[], totalCount=0, message=f"No semantic matches found for '{request.query_term}'.")

    # Apply pagination (though semantic search already limited by k)
    start_index = request.offset if request.offset else 0
    end_index = start_index + request.limit if request.limit else len(filtered_df)
    paginated_df = filtered_df.iloc[start_index:end_index]

    data_items: List[CoCostingItemView] = []
    for _, row in paginated_df.iterrows():
        item_view = CoCostingItemView(
            itemNo=row.get('itemNo'),
            material=row.get('material'),
            currency=row.get('currency'),
            price=row.get('price'),
            quantity=row.get('quantity'),
            supplier=row.get('supplier'),
            materialDesc=row.get('materialDesc'), 
            _reportType_csv=row.get('reportType'), # Include original reportType from CSV
            action=row.get('action'),
            activityType=row.get('activityType'),
            baseUnit=row.get('baseUnit'),
            businessArea=row.get('businessArea'),
            componentId=row.get('componentId'),
            costCenter=row.get('costCenter'),
            costElement=row.get('costElement'),
            costEstNo=row.get('costEstNo'),
            costingDate=row.get('costingDate'),
            costingType=row.get('costingType'),
            costingVersion=row.get('costingVersion'),
            currencyTypeCode=request.query_term, # Pass the query term back for context
            errMsg=row.get('errMsg'),
            fixValue=row.get('fixValue'),
            fixedValue=row.get('fixedValue'),
            itemCategory=row.get('itemCategory'),
            ledger=row.get('ledger'),
            materialCompositeKey=row.get('materialCompositeKey'),
            materialSpecProcTypeCosting=row.get('materialSpecProcTypeCosting'),
            mixedCosting=row.get('mixedCosting'),
            mixingRatio=row.get('mixingRatio'),
            operation=row.get('operation'),
            parentMaterial=row.get('parentMaterial'),
            parentMaterialCompositeKey=row.get('parentMaterialCompositeKey'),
            parentMaterialSpecProcTypeCosting=row.get('parentMaterialSpecProcTypeCosting'),
            parentPlant=row.get('parentPlant'),
            plant=row.get('plant'),
            priceUnit=row.get('priceUnit'),
            processCategory=row.get('processCategory'),
            profitCenter=row.get('profitCenter'),
            purcDocNum=row.get('purcDocNum'),
            purcItemNo=row.get('purcItemNo'),
            referenceObject=row.get('referenceObject'),
            selectionIdType=row.get('selectionIdType'),
            srcSys=row.get('srcSys'),
            totalValue=row.get('totalValue'),
            tranSelectionId=row.get('tranSelectionId'),
            transfCostEstNo=row.get('transfCostEstNo'),
            transfCostingDate=row.get('transfCostingDate'),
            transfCostingType=row.get('transfCostingType'),
            transfCostingVersion=row.get('transfCostingVersion'),
            transfValuationVariant=row.get('transfValuationVariant'),
            transferStrategy=row.get('transferStrategy'),
            valuationStrategy=row.get('valuationStrategy'),
            valuationVariant=row.get('valuationVariant'),
            workCenter=row.get('workCenter')
        )
        data_items.append(item_view)

    return SearchResultResponse(
        code=200,
        data=data_items,
        totalCount=len(filtered_df),
        message=f"Semantic search results for '{request.query_term}'."
    )
