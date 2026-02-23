package com.codebees.qubiqle;

import java.util.ArrayList;

import android.app.Activity;
import android.content.Context;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.TextView;

public class PendingInvoiceAdapter extends BaseAdapter
{
	private LayoutInflater mInflater1;
	private Activity activity;
	
	private ArrayList<InvoiceBean> arraylist_InvoiceBean;
	InvoiceBean invoiceData;
	
	public PendingInvoiceAdapter(Activity a, ArrayList<InvoiceBean> arrayList) {
		activity = a;
		mInflater1 = (LayoutInflater) activity
				.getSystemService(Context.LAYOUT_INFLATER_SERVICE);
		arraylist_InvoiceBean = arrayList;
	}

	@Override
	public int getCount() 
	{
		return arraylist_InvoiceBean.size();
	}

	@Override
	public Object getItem(int position) 
	{
		return position;
	}

	@Override
	public long getItemId(int position) {
		return position;
	}

	@Override
	public View getView(int position, View convertView, ViewGroup parent) 
	{
		View vi=convertView;
		try
		{ 
			// Inflate View
			vi = mInflater1.inflate(R.layout.pendinginvoiceitem, null);
			
			invoiceData = arraylist_InvoiceBean.get(position);
			
			//INITIALIZE TEXTVIEWS
			TextView invoice = (TextView)vi.findViewById(R.id.txt_invoiceno);
			TextView createdate = (TextView)vi.findViewById(R.id.txt_createddate);
            TextView restaurantname = (TextView)vi.findViewById(R.id.txt_restaurantname);

			//SET INVOICE NUM & CREATEDATE
			invoice.setText(invoiceData.getinvoice_number() == null ? "---" : invoiceData.getinvoice_number() );
			createdate.setText(invoiceData.getcreated_date());
			restaurantname.setText("");
		}
		
		catch (Exception e) {
			Log.e("Pending invoice Adapterr", "Message" + e);
		}
		
		return vi;
	}

}