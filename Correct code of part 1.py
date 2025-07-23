@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json
    # Validate required fields
    required_fields = ['name', 'sku', 'warehouse_id']
    for field in required_fields:
        if field not in data:
            return {"error": f"Missing required field: {field}"}, 400
    
    # Validate SKU uniqueness
    if Product.query.filter_by(sku=data['sku']).first():
        return {"error": "SKU must be unique"}, 400
    # Validate initial quantity if provided
    initial_quantity = data.get('initial_quantity', 0)
    if initial_quantity < 0:
        return {"error": "Initial quantity cannot be negative"}, 400
    
    try:
        # Start transaction
        db.session.begin()
        
        # Create new product
        product = Product(
            name=data['name'],
            sku=data['sku'],
            warehouse_id=data['warehouse_id']
        )
        db.session.add(product)
        db.session.flush()  # Get product ID without committing
        
        # Update inventory count
        inventory = Inventory(
            product_id=product.id,
            warehouse_id=data['warehouse_id'],
            quantity=initial_quantity
        )
        db.session.add(inventory)
        
        # Commit both operations together
        db.session.commit()
        
        return {"message": "Product created", "product_id": product.id}, 201
    
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}, 500
