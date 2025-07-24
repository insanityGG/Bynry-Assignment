@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
        # Get parameters with defaults
        days_sales_threshold = request.args.get('days_sales_threshold', default=30, type=int)
        min_sales_threshold = request.args.get('min_sales_threshold', default=1, type=int)
        # for low stock products with recent sales
        low_stock_alerts = []
        #products for company that have sales in last some days
        products_with_sales = db.session.query(Product).join(
            Inventory, Product.id == Inventory.product_id
        ).join(
            Sales, Product.id == Sales.product_id
        ).filter
        (Product.company_id == company_id,
            Sales.sale_date >= func.date_sub(func.current_date(), 
            days=days_sales_threshold)
        ).group_by(Product.id).having(
            func.sum(Sales.quantity) >= min_sales_threshold
        ).all()
        # Check inventory against thresholds
        for product in products_with_sales:
            # Get product threshold - assume it's stored in product table
            threshold = product.low_stock_threshold or 3  # Default threshold val
            # Get inventory across all warehouses
            inventory_items = Inventory.query.filter_by(
                product_id=product.id
            ).all()
            
            for inventory in inventory_items:
                if inventory.quantity <= threshold:
                    # Calculate days until stockout based on recent sales rate
                    sales_query = db.session.query(
                        func.sum(Sales.quantity).label('total_sales')
                    ).filter(
                        Sales.product_id == product.id,
                        Sales.sale_date >= func.date_sub(func.current_date(), 
                                                      days=days_sales_threshold)
                    ).first()
                    
                    total_sales = sales_query.total_sales or 1  # Avoid division by zero
                    daily_sales_rate = total_sales / days_sales_threshold
                    days_until_stockout = inventory.quantity / daily_sales_rate if daily_sales_rate > 0 else float('inf')
                    
                    # Get primary supplier for product
                    supplier = db.session.query(Supplier).join(
                        ProductSuppliers, Supplier.id == ProductSuppliers.supplier_id
                    ).filter(
                        ProductSuppliers.product_id == product.id
                    ).order_by(
                        ProductSuppliers.lead_time_days
                    ).first()
                    
                    if supplier:
                        warehouse = Warehouse.query.get(inventory.warehouse_id)
                        
                        alert = {
                            "product_id": product.id,
                            "product_name": product.name,
                            "sku": product.sku,
                            "warehouse_id": inventory.warehouse_id,
                            "warehouse_name": warehouse.name if warehouse else "Unknown",
                            "current_stock": inventory.quantity,
                            "threshold": threshold,
                            "days_until_stockout": round(days_until_stockout, 1),
                            "supplier": {
                                "id": supplier.id,
                                "name": supplier.name,
                                "contact_email": supplier.contact_email
                            }
                        }
                        low_stock_alerts.append(alert)
        
        return {
            "alerts": low_stock_alerts,
            "total_alerts": len(low_stock_alerts)
        }
        
    except Exception as e:
        return {"error": str(e)}, 500
