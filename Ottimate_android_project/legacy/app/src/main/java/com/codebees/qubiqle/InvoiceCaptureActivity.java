package com.codebees.qubiqle;

import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.UUID;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;


import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.entity.FileEntity;
import org.apache.http.entity.StringEntity;
import org.json.JSONArray;
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
import android.content.SharedPreferences.Editor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Bitmap.CompressFormat;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.Window;
import android.view.WindowManager;
import android.view.animation.Animation;
import android.view.animation.AnimationUtils;
import android.widget.AdapterView;
import android.widget.AdapterView.OnItemClickListener;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.ListView;

import org.apache.http.impl.client.DefaultHttpClient;


public class InvoiceCaptureActivity extends Activity 
{

	View hiddenPanel;

	private NetworkInfo netinfo = null, wifiinfo = null;
	ProgressDialog pd;
	Button btn_cancel;
	AlertDialog d;
	SharedPreferences sharedPreferences;
	Editor editor;
	ImageView iv_invoice;
	ImageView iv_logout;
	RestaurantBean restaurantBean;
	private ArrayList<RestaurantBean> arraylist_RestaurantBean;
	RestaurantListAdapter restaurantListAdapter;
	ListView lvrestaurants;
    File imageFile = null;
    Executor executor = Executors.newCachedThreadPool();

	protected void onCreate(Bundle savedInstanceState) {

		super.onCreate(savedInstanceState);

		//Remove title bar
		this.requestWindowFeature(Window.FEATURE_NO_TITLE);
		//Remove notification bar
		this.getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);

		try
		{
			//SET LAYOUT TO BE RENDERED
			setContentView(R.layout.invoice_capture);

			//GET INTERNET OR DATA CONNECTION INFORMATION
			ConnectivityManager conmng = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
			netinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_MOBILE);
			wifiinfo = conmng.getNetworkInfo(ConnectivityManager.TYPE_WIFI);

			//GET CONTROL IDS
			lvrestaurants = (ListView)findViewById(R.id.lv_restaurants);			
			hiddenPanel = findViewById(R.id.hidden_panel);

			// CLOSE RESTAURANT PANEL ON CANCEL CLICK
			btn_cancel=(Button)findViewById(R.id.btn_cancel);
			btn_cancel.setOnClickListener(new OnClickListener() 
			{
				public void onClick(View v) 
				{
					slideUpDown(hiddenPanel);
				}
			});

			// LOGOUT ACTIVITY
			iv_logout=(ImageView)findViewById(R.id.iv_logout);
			iv_logout.setOnClickListener(new OnClickListener() 
			{
				public void onClick(View v) 
				{
					//CONFIRMATION BEFORE LOGOUT
					AlertDialog.Builder builder=new AlertDialog.Builder(InvoiceCaptureActivity.this);
					builder.setMessage("Are you sure you want to logout?");
					builder.setCancelable(false);
					builder.setNegativeButton("No", new android.content.DialogInterface.OnClickListener() {

						@Override
						public void onClick(DialogInterface dialog, int which) 
						{
							dialog.cancel();
						}
					});

					builder.setPositiveButton("Yes", new android.content.DialogInterface.OnClickListener() {

						@Override
						public void onClick(DialogInterface dialog, int which) 
						{
							//CLEAR SHARED PREF
							Editor editor = getSharedPreferences(Constants.SharePref, 0).edit();
							editor.clear();
							editor.commit();
							Intent i = new Intent(InvoiceCaptureActivity.this,LoginActivity.class);
							startActivity(i);
							finish();
						}
					});

					d=builder.create();
					d.setTitle("LOGOUT");
					d.show();
				}
			});
			
			//PENDING INVOICES
			iv_invoice=(ImageView)findViewById(R.id.iv_invoice);
			iv_invoice.setOnClickListener(new OnClickListener() 
			{
				public void onClick(View v) 
				{
					//MOVE TO PENDING INVOICES
					Intent i = new Intent(InvoiceCaptureActivity.this,PendingInvoices.class);
					startActivity(i);
				}
			});


			//CHECK FOR ACTIVE INTERNET STATUS
			if ((netinfo.isAvailable() == true && netinfo.isConnected() == true) || (wifiinfo.isAvailable() == true && wifiinfo.isConnected() == true)) 
			{
				if(arraylist_RestaurantBean == null || arraylist_RestaurantBean.size() == 0)
					//INITIALIZE RESTAURANT ARRAY LIST 
					arraylist_RestaurantBean = new ArrayList<RestaurantBean>();
				//GET ALL RESTAURANTS
				GetAllRestaurants();
			}
			else
			{
				Dialog d = createAlertBox("No Internet Connectivity", "Please try again!!!");
				d.show();
				return;
			}
		}
		catch(Exception ex)
		{
			Log.e("Error", ex.toString());
		}
	}

	private void GetAllRestaurants()
	{
		try
		{
			// Show ProgressDialog
			pd = ProgressDialog.show(InvoiceCaptureActivity.this, "", "Get All Restaurants");

			AsyncHttpClient client = new AsyncHttpClient();
			// ADD AUTHORIZATION TOKEN FOR AUTH
			client.addHeader("Authorization", "Token " + Constants.token);
			
			// GET ALL RESTAURANTS MAKING HTTP CLIENT ASYNC CALL
			client.get(Constants.RestaurantsURL,  new AsyncHttpResponseHandler() {
				@Override
				public void onSuccess(String response) {
					// Hide Progress Dialog

					try 
					{
						//ON SUCCESS GETS RESTAURANT JSON ARRAY					
						JSONArray jsonArray = new JSONArray(response);
						if(jsonArray.length() > 0)
						{
							// JSON Object
							JSONObject obj = null;
							//LOOP THROUGH EACH RESTAURANT OBJECT IN THE JSON ARRAY
							for(int i = 0; i < jsonArray.length(); i++)
							{
								obj = jsonArray.getJSONObject(i);
								restaurantBean = new RestaurantBean();
								restaurantBean.setid(obj.getString("id").toString());
								restaurantBean.setname(obj.getString("name").toString());
								restaurantBean.setemail(obj.getString("email").toString());
								arraylist_RestaurantBean.add(restaurantBean);

								//Log.i("restaurant_id", restaurantBean.getid());
							}
						}


						if(arraylist_RestaurantBean.size() > 0)
						{
							//SET ADAPTER HERE
							restaurantListAdapter = new RestaurantListAdapter(InvoiceCaptureActivity.this, arraylist_RestaurantBean);
							lvrestaurants.setAdapter(restaurantListAdapter);
							// Hide ProgressDialog
							pd.cancel();
							lvrestaurants.setOnItemClickListener(new OnItemClickListener() {

								@Override
								public void onItemClick(AdapterView<?> arg0,
										View v, int position, long id) {
									// TODO Auto-generated method stub

									//GET RESTAURANT OBJECT
									restaurantBean = arraylist_RestaurantBean.get(position);
									Constants.restaurant_id = restaurantBean.getid();

									slideUpDown(hiddenPanel);
									
									//ACCESS CAMERA
									openCamera();
								}
							});
						}

					}
					catch (JSONException e) {
						// TODO Auto-generated catch block
						//Toast.makeText(getApplicationContext(), "Error Occured [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
						//e.printStackTrace();
						//Log.i("ERROR AT JSON", e.toString());
					}
				}

				// When the response returned by REST has Http response code other than '200'
				@Override
				public void onFailure(int statusCode, Throwable error,
						String content) {
					try 
					{
						//Log.i("FAILED", content);
						pd.cancel();
					}
					catch (Exception e) {

						//Toast.makeText(getApplicationContext(), "Error Occured [Server's JSON response might be invalid]!", Toast.LENGTH_LONG).show();
						//e.printStackTrace();

					}
				}
			});
		}
		catch(Exception ex)
		{
			//Log.e("Error at GetAllRestaurants", ex.toString());
		}
	}


	// GET Image Details
	String mCurrentPhotoPath, imageName;
	static final int REQUEST_TAKE_PHOTO = 1;
    public void openCamera()
	{
		// Access the camera	
		Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
		if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
			try
			{
                imageFile = createImageFile();
			} 
			catch (IOException ex) {
				// Error occurred while creating the File
			}

			if (imageFile != null) {
                takePictureIntent.putExtra(android.provider.MediaStore.EXTRA_OUTPUT,Uri.fromFile(imageFile));
				startActivityForResult(takePictureIntent, REQUEST_TAKE_PHOTO);
			}
		}
	}

	private File createImageFile() throws IOException {
		// Create an image file name
		String storageDir = Environment.getExternalStorageDirectory() + "/qubiqle";
		File dir = new File(storageDir);
        try {
            if (!dir.exists()) {
                dir.mkdir();
            }
        } catch(Exception e) {
            storageDir = Environment.getDataDirectory() + "/qubiqle";
            dir = new File(storageDir);
            if (!dir.exists()) {
                dir.mkdir();
            }
        }
		File savedImage = new File(storageDir + "/" + UUID.randomUUID().toString() + ".jpg");

		mCurrentPhotoPath = savedImage.getAbsolutePath();
		imageName = savedImage.getName();
		return savedImage;
	}

	@Override
	protected void onActivityResult(int requestCode, int resultCode, Intent data) 
	{
		// Send invoice	
		//Log.i("RESULT", String.valueOf(resultCode));
		if (requestCode == REQUEST_TAKE_PHOTO && resultCode == Activity.RESULT_OK) 
		{
            final File tempFile = imageFile;

            executor.execute(new Runnable() {

                public void run() {
                    Bitmap unscaledBitmap = BitmapFactory.decodeFile(tempFile.getAbsolutePath());

                    try {
                        double twoMegaPixel = 2 * 1024 * 1024;
                        //Assume that all cameras are atleast 2MP
                        double scale = (unscaledBitmap.getHeight() * unscaledBitmap.getWidth()) / twoMegaPixel;
                        scale = Math.sqrt(scale);

                        Bitmap scaledBitmap = Bitmap.createScaledBitmap(unscaledBitmap, (int) (unscaledBitmap.getWidth() / scale), (int) (unscaledBitmap.getHeight() / scale), true);
                        File savedImage = createImageFile();
                        try {
                            FileOutputStream fo = new FileOutputStream(savedImage);
                            scaledBitmap.compress(CompressFormat.JPEG, 100, fo);
                            fo.flush();
                            fo.close();

                            sendInvoice(savedImage);

                        } catch (FileNotFoundException e) {
                            e.printStackTrace();
                        } catch (IOException e) {
                            e.printStackTrace();
                        }
                    } catch (Exception ex) {
                        Log.e("ERROR AT RESIZING IMAGE TO 2MP", ex.toString());
                        ex.printStackTrace();
                    }
                }
            });

            new Handler(Looper.getMainLooper()).post(new Runnable() {
                @Override
                public void run() {
                    openCamera();
                }
            });
		}
	}

	private class UploadImageAsync extends AsyncTask<String, String, String> 
	{
        private final File invoiceImage;
        private final JSONObject signedInvoiceResponse;
        ProgressDialog pd;

        public UploadImageAsync(JSONObject signedInvoice,File image) {
            this.invoiceImage = image;
            this.signedInvoiceResponse    = signedInvoice;
        }

        // Upload invoice to s3
		protected void onPreExecute() {
			//pd = ProgressDialog.show(InvoiceCaptureActivity.this, "", "Uploading Image");
		}

		@Override
		protected String doInBackground(String... arg0) {
			// TODO Auto-generated method stub

//            signedFileName = obj.getString("file_name");
//            signedUploadID = obj.getString("upload_id");
//            signedImageURL = obj.getString("url");
//            signedPath = obj.getString("path");

            //uploadFile(mCurrentPhotoPath);
			uploadToS3(invoiceImage);
			return null;
		}

		protected void onPostExecute(String result) 
		{
			// Create invoice
			//pd.cancel();
			createInvoice(signedInvoiceResponse);
		}

        private void uploadToS3(File image)
        {
            try
            {
                HttpPut put = new HttpPut(signedInvoiceResponse.getString("put_request"));

                FileEntity entity = new FileEntity(image, "image/jpeg");
                //HttpClient httpClient = HttpClientBuilder.create().build();
                HttpClient httpClient = new DefaultHttpClient();
                put.addHeader("Content-type", "image/jpeg");

                put.setEntity(entity);

                // HTTPClient Response
                HttpResponse response;
                try {
                    response = httpClient.execute(put);
                    //HttpEntity responseEntity = response.getEntity();
                    if(response.getStatusLine().getStatusCode() == HttpStatus.SC_OK ||
                            response.getStatusLine().getStatusCode() == HttpStatus.SC_CREATED)
                    {

                        //Log.i("MESSAGE",responseEntity.toString());
                    }
                    else
                    {
                        //System.out.println(responseEntity);
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
            catch(Exception ex)
            {
                Log.i("ERROR While posting to S3", ex.toString());
            }
        }
	}


	public void slideUpDown(final View view) 
	{
		if (!isPanelShown()) 
		{
			// Show the panel
			Animation bottomUp = AnimationUtils.loadAnimation(this,
					R.anim.bottom_up);

			hiddenPanel.startAnimation(bottomUp);
			hiddenPanel.setVisibility(View.VISIBLE);
		}
		else {
			// Hide the Panel
			Animation bottomDown = AnimationUtils.loadAnimation(this,
					R.anim.bottom_down);

			hiddenPanel.startAnimation(bottomDown);
			hiddenPanel.setVisibility(View.GONE);
		}
	}

	private boolean isPanelShown() {

		// Show the HiddenPanel
		return hiddenPanel.getVisibility() == View.VISIBLE;
	}

	/** AlertBox **/
	public Dialog createAlertBox(String title, String message) 
	{
		// Create AlertBox
		return new AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("OK", new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int whichButton) {
			}
		}).create();
	}

	private void sendInvoice(final File image)
	{
		try
		{
			// Request Parameters
			RequestParams params = new RequestParams();
			params.add("filename", imageName);

			AsyncHttpClient client = new AsyncHttpClient();
			// ADD AUTHORIZATION TOKEN FOR AUTH
			client.addHeader("Authorization", "Token " + Constants.token);
			//client.addHeader("Content-type", "image/jpeg");
			client.get(Constants.signedS3URL, params ,new AsyncHttpResponseHandler() {

				@Override
				public void onSuccess(String response) {
					try {

						JSONObject obj = new JSONObject(response);
                        new UploadImageAsync(obj,image).execute("");

					} catch (JSONException e) {
						// TODO Auto-generated catch block
						e.printStackTrace();
					}
				}

				@Override
				public void onFailure(int statusCode, Throwable error, String content) {
					Log.i("FAILED", content);
				}
			});
		} //End try block
		catch(Exception ex)
		{
			Log.e("Exception AT SEND INVOICE", ex.toString());
		}
	}

	private void createInvoice(JSONObject signedInvoiceResponse)
	{
		try
		{
			//Log.i("PARAMS", Constants.restaurant_id + " "  +signedUploadID  + " " + signedImageURL);

			//creating an Invoice

			JSONObject param = new JSONObject();
			param.put("restaurant", Constants.restaurant_id);
			param.put("upload_id", signedInvoiceResponse.get("upload_id"));
			param.put("image", signedInvoiceResponse.get("url"));


			StringEntity entity = new StringEntity(param.toString());


			AsyncHttpClient client = new AsyncHttpClient();
			// ADD AUTHORIZATION TOKEN FOR AUTH
			client.addHeader("Authorization", "Token " + Constants.token);
			client.addHeader("Accept", "application/json");
			client.addHeader("Content-type", "application/json");

			client.post(getApplicationContext(), Constants.createInvoiceURL, entity, "application/json", new AsyncHttpResponseHandler() {
				@Override
				public void onSuccess(String response) {
					// Hide Progress Dialog

					try 
					{
						//JSONObject jsonObj;
						//jsonObj = new JSONObject(response);
						//JSONObject resultObj = jsonObj.getJSONObject("results");
						//Log.i("STRING RE", resultObj.toString());
						//Log.i("STRING RESPONSE", response);

					} // End try block

					catch (Exception e) {
						// TODO Auto-generated catch block
						//e.printStackTrace();
					} 


				}

				@Override
				public void onFailure(int statusCode, Throwable error,
						String content) {
					//Log.i("FAILED", content);
				}
			});
		} // end try block
		catch(Exception ex)
		{
			//Error in create Invoice
			//Log.e("ERROR WHILE CREATING INVOICE", ex.toString());
		}
	} 
}

