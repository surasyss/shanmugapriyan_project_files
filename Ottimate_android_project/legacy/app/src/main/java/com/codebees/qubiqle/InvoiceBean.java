package com.codebees.qubiqle;

public class InvoiceBean 
{
	private String count;
	private String id;
	private String restaurant;
	private String invoice_number;
	private String created_date;
	
	//GET & SET PENDING INVOICE FIELDS
	public String getcount() {
		return count;
	}
	public void setcount(String count) {
		this.count = count;
	}
	
	public String getid() {
		return id;
	}
	public void setid(String id) {
		this.id = id;
	}
	
	public String getrestaurant() {
		return restaurant;
	}
	public void setrestaurant(String restaurant) {
		this.restaurant = restaurant;
	}
	
	public String getinvoice_number() {
		return invoice_number;
	}
	public void setinvoice_number(String invoice_number) {
		this.invoice_number = invoice_number;
	}
	
	public String getcreated_date() {
		return created_date;
	}
	public void setcreated_date(String created_date) {
		this.created_date = created_date;
	}
	
}
