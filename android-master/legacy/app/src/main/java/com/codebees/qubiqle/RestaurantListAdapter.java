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

public class RestaurantListAdapter extends BaseAdapter {

	private LayoutInflater mInflater1;
	private Activity activity;


	private ArrayList<RestaurantBean> arraylist_RestaurantBean ;
	RestaurantBean restaurantData;
	
	// Inflate ArrayList Adapter

	public RestaurantListAdapter(Activity a, ArrayList<RestaurantBean> arrayList) {
		activity = a;
		mInflater1 = (LayoutInflater) activity
				.getSystemService(Context.LAYOUT_INFLATER_SERVICE);
		arraylist_RestaurantBean = arrayList;
	}

	@Override
	public int getCount() {
		// TODO Auto-generated method stub
		return arraylist_RestaurantBean.size();
	}

	@Override
	public Object getItem(int position) {
		// TODO Auto-generated method stub
		return position;
	}

	@Override
	public long getItemId(int position) {
		// TODO Auto-generated method stub
		return position;
	}

	@Override
	public View getView(int position, View convertView, ViewGroup parent) {

		View vi= convertView;

		try
		{ 
			// Inflate View
			vi = mInflater1.inflate(R.layout.restaurantlistitem, null);
			
			restaurantData = arraylist_RestaurantBean.get(position);

			TextView label = (TextView)vi.findViewById(R.id.txtView_Label);
			
			// set Restaurant Name
			label.setText(restaurantData.getname());

		}
		catch (Exception e) {
			Log.e("Restaurant Adapter", "Message" + e);
		}

		return vi;
	}

}