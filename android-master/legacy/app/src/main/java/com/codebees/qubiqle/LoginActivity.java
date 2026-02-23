package com.codebees.qubiqle;

import org.json.JSONException;
import org.json.JSONObject;

import com.loopj.android.http.AsyncHttpClient;
import com.loopj.android.http.AsyncHttpResponseHandler;
import com.loopj.android.http.RequestParams;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Bundle;
import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.View.OnClickListener;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;


public class LoginActivity extends Activity 
{
	public Button btn_login;
	private String errorMessage = "";
	private String token = "";
	private SharedPreferences sharedpreferences;

	private EditText etuserName, etpassword;
	private NetworkInfo netinfo = null, wifiinfo = null;
	ProgressDialog pd;

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
			setContentView(R.layout.main_login);

			// INTERNET COnnectivity references
			ConnectivityManager conmng = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
			final InputMethodManager imm = (InputMethodManager)getSystemService(
					Context.INPUT_METHOD_SERVICE);
			netinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_MOBILE);
			wifiinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_WIFI);
			sharedpreferences = getSharedPreferences(Constants.SharePref, 0);

			// INTIALIZE EDITTEXTS
			etuserName = (EditText)findViewById(R.id.et_username);
			etpassword = (EditText)findViewById(R.id.et_password);


			// LOGIN Activity
			etpassword.setOnEditorActionListener(new EditText.OnEditorActionListener() {
				public boolean onEditorAction(TextView v, int actionId,
						KeyEvent event) {
					// TODO Auto-generated method stub

					// Authenticating LOGIN
					if (actionId == EditorInfo.IME_ACTION_DONE
							|| actionId == EditorInfo.IME_ACTION_NEXT) {

						imm.hideSoftInputFromWindow(etpassword.getWindowToken(), 0);
						token = "";
						errorMessage = "";
						AuthenticateLogin();
						return false;
					}
					return false;
				}
			});

			// LOGIN Button declaration
			btn_login = (Button)findViewById(R.id.btn_login);

			// OnClick event for LOGIN
			btn_login.setOnClickListener(new OnClickListener() {

				@Override
				public void onClick(View v) {
					// TODO Auto-generated method stub
					//LoginButtonHandler();

					//HIDING KEYPAD
					imm.hideSoftInputFromWindow(etpassword.getWindowToken(), 0);
					token = "";
					errorMessage = "";
					AuthenticateLogin();
				}
			});

			//CHECK FOR INTERNET OR MOBILE CONNECTION
			if ((netinfo.isAvailable() == true && netinfo.isConnected() == true) 
					|| (wifiinfo.isAvailable() == true && wifiinfo.isConnected() == true)) 
			{
				//IF USERNAME ALREADY EXISTS IN THE SHARED PREFS
				if (sharedpreferences.contains("username"))
				{
					Constants.token = sharedpreferences.getString("token", "");
					// MOVE TO THE NEXT SCREEN FOR SCANNING THE INVOICE
					Intent i = new Intent(LoginActivity.this, InvoiceCaptureActivity.class);
					i.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_NEW_TASK);
					startActivity(i);
				}
			}
		}
		catch(Exception e)
		{
			Log.e("Error", e.toString());
		}
	}

	private void AuthenticateLogin()
	{
		//  Check Internet Connection
		if(!etuserName.getText().toString().equals("") || !etpassword.getText().toString().equals(""))
			if ((netinfo.isAvailable() == true && netinfo.isConnected() == true) || (wifiinfo.isAvailable() == true && wifiinfo.isConnected() == true)) 
			{

			}
			else
			{
				Dialog d = createAlertBox("No Internet Connectivity", "Please try again!!!");
				d.show();
				return;
			}
		else
		{
			Toast.makeText(getApplicationContext(), "Username and Password cannot be blank",Toast.LENGTH_LONG).show();
			return;
		}

		// Activate progress dialog
		pd = ProgressDialog.show(LoginActivity.this, "", "Authenticating your Login");

		//Requesting parameters
		RequestParams params = new RequestParams();
		// Put Http parameter username with value of Email Edit View control
		params.add("username", etuserName.getText().toString());
		// Put Http parameter password with value of Password Edit Value control
		params.add("password", etpassword.getText().toString());


		//MAKE ASYNC HTTP CLIENT POST 
		AsyncHttpClient client = new AsyncHttpClient();
		client.post(Constants.LoginAuthURL, params ,new AsyncHttpResponseHandler() {
			// When the response returned by REST has Http response code '200'
			@Override
			public void onSuccess(String response) {

				try 
				{
					// JSON Object
					JSONObject obj = new JSONObject(response);
					
					token = obj.getString("token");				

					// Hide Progress Dialog
					pd.cancel();
					if(token.trim().length() > 0)
					{
						// Get TOKEN onSuccess
						Constants.token = token;

						//STORING REQ INFO IN SHARED PREFS
						String sUsername = etuserName.getText().toString().trim();
						String sPassword = etpassword.getText().toString().trim();
						SharedPreferences.Editor Editor = sharedpreferences.edit();
						Editor.putString("username", sUsername);
						Editor.putString("password", sPassword);
						Editor.putString("token", token);

						Editor.commit();

						// MOVE TO THE NEXT SCREEN FOR SCANNING THE INVOICE
						Intent i = new Intent(LoginActivity.this, InvoiceCaptureActivity.class);
						i.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_NEW_TASK);
						startActivity(i);
					}

				} catch (JSONException e) {
					token = "";
					// TODO Auto-generated catch block
					//Toast.makeText(getApplicationContext(), "Error Occured [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
					//e.printStackTrace();
					//Log.i("ERROR AT JSON", token);
				}
			}
			// When the response returned by REST has Http response code other than '200'
			@Override
			public void onFailure(int statusCode, Throwable error,
					String content) {
				try 
				{
					// Stop ProgressDialog
					pd.cancel();
					// JSON Object
					// Error Response From Server
					if(statusCode == 401)
					{
						errorMessage = content.replace("\"", "");
						//Log.i("errorMessage", errorMessage);
						// Toast Error Message
						if(errorMessage.trim().length() > 0)
						{
							Toast.makeText(getApplicationContext(), errorMessage, Toast.LENGTH_LONG).show();
						}
					}
				}
				catch (Exception e) {
					// TODO Auto-generated catch block
					//Toast.makeText(getApplicationContext(), "Error Occured [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
					e.printStackTrace();

				}
				// When Http response code is '404'
				if(statusCode == 404){
					//Toast.makeText(getApplicationContext(), "Requested resource not found", Toast.LENGTH_LONG).show();
				} 
				// When Http response code is '500'
				else if(statusCode == 500){
					//Toast.makeText(getApplicationContext(), "Something went wrong at server end", Toast.LENGTH_LONG).show();
				} 
				// When Http response code other than 404, 500
				else{
					//Toast.makeText(getApplicationContext(), "Unexpected Error occcured! [Most common Error: Device might not be connected to Internet or remote server is not up and running]", Toast.LENGTH_LONG).show();
				}
			}
		});
	}


	/** AlertBox **/
	public Dialog createAlertBox(String title, String message) 
	{
		// Create Alertbox
		return new AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("OK", new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int whichButton) {
			}
		}).create();
	}
}
