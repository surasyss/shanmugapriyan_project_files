package com.qubiqle.plateiq;

import android.os.Bundle;
import com.facebook.react.ReactActivity;
import io.branch.rnbranch.*;
import android.content.Intent;


public class MainActivity extends ReactActivity {

  /**
   * Returns the name of the main component registered from JavaScript. This is used to schedule
   * rendering of the component.
   */
  @Override
  protected String getMainComponentName() {
    return "MobileApp";
  }

  @Override
  protected void onCreate(Bundle savedInstanceState) {
     super.onCreate(null);
 }

   @Override
   protected void onStart() {
       super.onStart();
       RNBranchModule.initSession(getIntent().getData(), this);
   }

   @Override
   public void onNewIntent(Intent intent) {
       super.onNewIntent(intent);
       setIntent(intent);
   }
}
