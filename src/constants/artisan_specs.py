"""Artisan specifications dictionary and related constants"""

# ---------- Artisan Specifications Dictionary ----------
ARTISAN_SPECIFICATIONS = {
    # Basic Physical Properties
    "material": "Primary material used (e.g., Cotton, Silk, Wool, Bamboo, Wood, Clay, Metal, Leather, Jute, Hemp)",
    "secondary_material": "Additional materials used (e.g., Cotton lining, Metal clasps, Wooden handles, Silk threads)",
    "colour": "Primary color or color combination (e.g., Red, Blue, Multicolor, Natural, Indigo, Saffron)",
    "pattern": "Design pattern or motif (e.g., Floral, Geometric, Paisley, Stripes, Plain, Abstract, Traditional)",
    
    # Dimensions
    "length": "Product length with units (e.g., 2 meters, 15 cm, 6 feet)",
    "width": "Product width with units (e.g., 1 meter, 10 cm, 3 feet)",
    "height": "Product height with units (e.g., 20 cm, 1 foot, 5 inches)",
    "diameter": "Circular product diameter (e.g., 25 cm, 10 inches)",
    "thickness": "Material thickness (e.g., 2mm, 0.5 inch, Lightweight, Heavy)",
    "weight": "Product weight (e.g., 200g, 1.5 kg, 3 pounds)",
    
    # Origin and Craftsmanship
    "state_region": "Specific state or region (e.g., Gujarat, Rajasthan, West Bengal, Kashmir, Odisha)",
    "craft_style": "Traditional craft technique (e.g., Ikat, Kalamkari, Chikankari, Phulkari, Warli, Madhubani)",
    "weaving_technique": "Specific weaving method (e.g., Handloom, Powerloom, Jacquard, Dobby, Plain weave)",
    "artisan_community": "Artisan group or community (e.g., Karigars, Weavers, Potters, Metalworkers)",
    
    # Shape and Structure
    "shape": "Overall shape (e.g., Rectangular, Circular, Square, Oval, Irregular, Curved)",
    "silhouette": "Overall form (e.g., A-line, Straight, Flared, Fitted, Loose, Structured)",
    "neckline": "Neck design for clothing (e.g., Round, V-neck, Boat neck, High neck, Collar)",
    "sleeve_type": "Sleeve style (e.g., Full sleeve, Half sleeve, Sleeveless, Bell sleeve, Cap sleeve)",
    
    # Technical Specifications
    "thread_count": "Fabric density (e.g., 200 TPI, High, Medium, Low)",
    "gsm": "Grams per square meter for textiles (e.g., 150 GSM, 300 GSM)",
    "yarn_type": "Type of yarn used (e.g., Single ply, Double ply, Twisted, Mercerized)",
    "finish": "Surface treatment (e.g., Matte, Glossy, Textured, Smooth, Embossed)",
    "lining": "Interior lining details (e.g., Cotton lined, Unlined, Silk lined, Padded)",
    
    # Functional Aspects
    "occasion": "Suitable occasions (e.g., Festive, Daily wear, Wedding, Ceremony, Casual, Formal)",
    "season": "Appropriate season (e.g., Summer, Winter, Monsoon, All season)",
    "age_group": "Target age group (e.g., Adult, Children, Elderly, Unisex, Women, Men)",
    "care_instructions": "Maintenance guide (e.g., Hand wash, Dry clean, Machine wash, Air dry)",
    "usage": "Primary use (e.g., Decorative, Functional, Ceremonial, Daily use)",
    
    # Artistic Elements
    "embellishment": "Decorative elements (e.g., Embroidery, Beadwork, Sequins, Mirror work, Tassels)",
    "border_style": "Edge design (e.g., Contrast border, Woven border, Embroidered, Plain, Fringed)",
    "motif_inspiration": "Design inspiration (e.g., Nature, Religious, Geometric, Cultural, Modern)",
    "color_technique": "Coloring method (e.g., Natural dyes, Chemical dyes, Tie-dye, Block print, Hand painted)",
    
    # Quality and Durability
    "quality_grade": "Quality level (e.g., Premium, Standard, Economy, Luxury, Artisan grade)",
    "durability": "Expected lifespan (e.g., High durability, Medium, Delicate, Long-lasting)",
    "fade_resistance": "Color fastness (e.g., Fade resistant, Moderate, Requires care)",
    "shrinkage": "Shrinkage potential (e.g., Pre-shrunk, Minimal shrinkage, May shrink)",
    
    # Certification and Standards
    "organic_certified": "Organic certification (e.g., GOTS certified, Organic cotton, Natural materials)",
    "fair_trade": "Fair trade status (e.g., Fair trade certified, Ethically made, Artisan supported)",
    "handmade_level": "Handmade percentage (e.g., 100% handmade, Semi-handmade, Machine assisted)",
    
    # Packaging and Presentation
    "packaging": "How it's packaged (e.g., Eco-friendly box, Cloth bag, Plastic wrap, Gift wrapped)",
    "set_includes": "What's included (e.g., Single piece, Set of 2, With accessories, Matching items)",
    
    # Cultural and Historical
    "cultural_significance": "Cultural importance (e.g., Traditional wear, Ceremonial use, Regional pride)",
    "historical_period": "Historical style (e.g., Mughal era, Colonial period, Modern, Ancient)",
    "symbolism": "Symbolic meaning (e.g., Prosperity, Protection, Celebration, Spiritual)",
    
    # Business and Pricing
    "production_time": "Time to make (e.g., 1 week, 2 days, 1 month, On demand)",
    "customization": "Customization options (e.g., Color options, Size options, Personalization, Custom design)",
    "minimum_order": "Minimum quantity (e.g., 1 piece, 5 pieces, 10 pieces, No minimum)",
    
    # Special Features
    "unique_features": "Special characteristics (e.g., Reversible, Washable, Lightweight, Multipurpose)",
    "texture": "Surface feel (e.g., Soft, Rough, Smooth, Coarse, Silky, Grainy)",
    "transparency": "Light transmission (e.g., Opaque, Semi-transparent, Sheer, Thick)",
    "stretchability": "Flexibility (e.g., Stretchable, Non-stretch, Slightly elastic, Rigid)",
}

# Bot stages
STAGES = [
    "await_initial_choice",
    "upload_product_llm_image", 
    "upload_product_llm_name",
    "upload_product_llm_price",
    "upload_product_llm_specs",
    "ask_query_llm",
    "done"
]

# Default specifications for fallback
DEFAULT_FALLBACK_SPECS = {
    "material": "What is the primary material of your product?",
    "colour": "What is the main color of your product?",
    "craft_style": "What traditional craft technique was used for this product?",
    "occasion": "What occasions is this product suitable for?",
    "care_instructions": "How should this product be maintained?"
}
