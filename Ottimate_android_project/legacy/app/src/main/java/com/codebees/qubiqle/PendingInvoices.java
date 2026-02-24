package com.codebees.qubiqle;

import java.util.ArrayList;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import com.loopj.android.http.AsyncHttpClient;
import com.loopj.android.http.AsyncHttpResponseHandler;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;

import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.Window;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.ListView;
import android.widget.TextView;


public class PendingInvoices extends Activity
{
	private NetworkInfo netinfo = null, wifiinfo = null;
	TextView tv_back;
	ImageView iv_back;
	ProgressDialog pd;
	ListView lv_invoicelist;
	AlertDialog d;
	InvoiceBean invoiceBean;
	PendingInvoiceAdapter pendingInvoiceAdapter;
	private ArrayList<InvoiceBean> arraylist_InvoiceBean;

	protected void onCreate(Bundle savedInstanceState) 
	{
		super.onCreate(savedInstanceState);

		//Remove title bar
		this.requestWindowFeature(Window.FEATURE_NO_TITLE);
		//Remove notification bar
		this.getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
		
		try
		{
		
			//SET LAYOUT TO BE RENDERED
			setContentView(R.layout.pending_invoices);
			
			//GET INTERNET OR DATA CONNECTION INFORMATION
			ConnectivityManager conmng = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
			netinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_MOBILE);
			wifiinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_WIFI);
			
			if ((netinfo.isAvailable() == true && netinfo.isConnected() == true) || (wifiinfo.isAvailable() == true && wifiinfo.isConnected() == true)) 
			{
				//INITIALIZE RESTAURANT ARRAY LIST 
				arraylist_InvoiceBean = new ArrayList<InvoiceBean>();
				//GET PendingInvoiceList
				GetPendingInvoiceList();
			}
			else
			{
				Dialog d = createAlertBox("No Internet Connectivity", "Please try again!!!");
				d.show();
				return;
			}	
			
			lv_invoicelist = (ListView)findViewById(R.id.lv_invoicelist);
			
			// NAVIGATE TO INVOICEACTIVITY ON BACK CLICK
			tv_back=(TextView)findViewById(R.id.tv_back);
			tv_back.setOnClickListener(new OnClickListener() 
			{
				
				public void onClick(View v) 
				{
					finish();
				}
			});
								
			// NAVIGATE TO INVOICEACTIVITY ON BACK CLICK
			iv_back=(ImageView)findViewById(R.id.iv_back);
			iv_back.setOnClickListener(new OnClickListener() 
			{
				
				public void onClick(View v) 
				{
					finish();
				}
			});
			
		}
		catch(Exception ex)
		{
			Log.e("Error", ex.toString());
		}
			
	}

	@Override
	public void onBackPressed() {
		this.finish();
	}
	private void GetPendingInvoiceList() 
	{
		try
		{
			
			// Show Progress Dialog
			pd = ProgressDialog.show(PendingInvoices.this,  "", "Loading Pending Invoices");
			
			AsyncHttpClient client = new AsyncHttpClient();
			//ADD AUTHORIZATION TOKEN
			client.addHeader("Authorization", "Token " + Constants.token);
			//Log.i("TOKEN", Constants.token);
			client.get(Constants.createInvoiceURL + "?state=pending", new AsyncHttpResponseHandler()
			{
				@Override
				public void onSuccess(String response)
				{
					try
					{
						//Log.i("step1", "Success");
						//ON SUCCESS GETS RESTAURANT JSON ARRAY
						JSONObject jsonobject= new JSONObject(response);
						
						if(jsonobject!= null)
						{
							// JSON Object
							JSONObject obj = null;
							JSONArray invoiceArray = jsonobject.getJSONArray("results");
							//Log.i("step2", "Success");
							for(int i = 0; i<invoiceArray.length(); i++)
							{
								obj = invoiceArray.getJSONObject(i);
								invoiceBean = new InvoiceBean();
								
								invoiceBean.setid(obj.getString("id").toString());
								invoiceBean.setrestaurant(obj.getString("restaurant").toString());
								invoiceBean.setinvoice_number(obj.getString("invoice_number").toString());
								invoiceBean.setcreated_date(obj.getString("created_date").toString());
								//invoiceBean.setthumbnail(obj.getString("thumbnail").toString());
								//invoiceBean.setname(obj.getString("name").toString());
								arraylist_InvoiceBean.add(invoiceBean);
								
								
							}
						}

						{
							//SET ADAPTER HERE
							pendingInvoiceAdapter = new PendingInvoiceAdapter(PendingInvoices.this, arraylist_InvoiceBean);
							lv_invoicelist.setAdapter(pendingInvoiceAdapter);
							pd.cancel();
						}
					}
					
					catch (JSONException e) {
						// TODO Auto-generated catch block
						//Toast.makeText(getApplicationContext(), "Error Occurred [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
						e.printStackTrace();
						Log.i("ERROR AT JSON", e.toString());
					}
				}
				
				// When the response returned by REST has Http response code other than '200'
				@Override
				public void onFailure(int statusCode, Throwable error,
						String content) {
					try 
					{
						Log.i("FAILED", content);
						pd.cancel();
					}
					catch (Exception e) {

						//Toast.makeText(getApplicationContext(), "Error Occured [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
						e.printStackTrace();

					}
				}
			});
		}
		
		catch(Exception ex)
		{
			Log.e("Error at GetAllRestaurants", ex.toString());
		}
	}		

	public Dialog createAlertBox(String title, String message) 
	{
		// Create AlertBox
		return new AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("OK", new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int whichButton) {
			}
		}).create();
	}
	
}
	