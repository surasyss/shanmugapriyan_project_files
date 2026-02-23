import React from 'react';
import {
  View, Text, Image, TouchableOpacity, Platform, ActivityIndicator
} from 'react-native';
import Modal from 'react-native-modal';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import ScrollableTabView from 'react-native-scrollable-tab-view';
import styles from './styles';
import { parserInvoiceDate, parserInvoiceTime } from '../../../utils/DateFormatter';
import DetailsTabBar from '../../qubiqle/DetailsTabBar';
import LineItems from '../../qubiqle/LineItems';
import GlSplits from '../../qubiqle/GlSplits';
import InvoiceImages from '../../qubiqle/InvoiceImages';
import SwipeButton from '../../qubiqle/SwipeButton/src/components/SwipeButton';
import Colors from '../../../styles/Colors';
import Images from '../../../styles/Images';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import { replaceAll, title, toCurrencyNoSpace } from '../../../utils/StringFormatter';
import Spinner from '../../qubiqle/Spinner';
import Timeline from '../../qubiqle/Timeline';
import MentionsTextInput from '../../qubiqle/MentionsTextInput';

class InvoiceDetail extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isApproved: props.invoice.isApproved,
      filteredUsers: []
    };
  }

  onTabSelection = (index) => {
    const { invoice, setCurrentTab } = this.props;
    if (index.i === 0) sendMixpanelEvent(MixpanelEvents.INVOICE_ITEMS_OPENED, { invoice });
    else if (index.i === 1) sendMixpanelEvent(MixpanelEvents.INVOICE_GL_SPLITS_OPENED, { invoice });
    else if (index.i === 2) sendMixpanelEvent(MixpanelEvents.INVOICE_IMAGES_OPENED, { invoice });
    else if (index.i === 3) sendMixpanelEvent(MixpanelEvents.INVOICE_HISTORY_OPENED, { invoice });
    if (setCurrentTab) {
      setCurrentTab(index.i);
    }
  };

  onSuggestionTap(item, hidePanel) {
    hidePanel();
    const { name } = item;
    const { flagText, setFlagText } = this.props;
    const comment = flagText.slice(0, -this.state.keyword.length);
    setFlagText(`${comment}@${name} `);
  }

  getFlagText() {
    const { users } = this.props;
    let { flagText } = this.props;
    users.forEach((user) => {
      flagText = replaceAll(flagText, `@${user.name}`, `{{@${user.id}}}`);
    });
    return flagText;
  }

  getHistoryMessage(activity) {
    let message = activity.reason;
    if (activity.resolving) {
      message = 'Resolve Flag';
    }
    if (activity.user) {
      if (message.toLowerCase() === 'approved' && activity.user.email.toLowerCase() === 'support@plateiq.com') {
        return message;
      }
      message += ` By ${activity.user.display_name}`;
    }
    return message;
  }

  getHistoryDescription(activity) {
    const { users } = this.props;
    const { message } = activity;

    const result: string[] = [];
    if (message && typeof (message) === 'string') {
      message.split('/n').forEach((msg) => {
        const line: string[] = [];
        let count = 0;
        while (msg && msg.includes('{{@')) {
          const left_index = msg.indexOf('{{@');
          const right_index = msg.indexOf('}}');
          const user_id = msg.substr(left_index + 3, right_index - left_index - 3);
          let username = null;

          // Save the string before the {{@
          line.push(msg.substr(0, left_index));

          // Find matched user, and add @username to line
          for (let i = 0; i < users.length; i++) {
            if (`${users[i].id}` === `${user_id}`) {
              username = users[i].name;
              line.push(`@${username}`);
              break;
            }
          }

          // Then message is become the substring after }}
          msg = msg.substr(right_index + 2);

          if (!username || ++count > users.length) {
            break;
          }
        }

        // Add rest string
        line.push(msg);
        result.push(line.join('').toString());
      });
    }
    return result.join('\n');
  }

  callback(keyword) {
    if (this.reqTimer) {
      clearTimeout(this.reqTimer);
    }

    this.reqTimer = setTimeout(() => {
      const searchKey = keyword.slice(1);
      const { users } = this.props;
      const filteredUsers = [];
      users.forEach((user) => {
        if (user.name.indexOf(searchKey) !== -1) filteredUsers.push(user);
      });
      this.setState({
        keyword,
        filteredUsers
      });
    }, 200);
  }

  renderHeader() {
    const { invoice, restaurants } = this.props;
    let vendor_name = '';
    const {
      vendor_obj, invoice_number, date, total_amount, is_vendor_supplied_invoice, is_flagged
    } = invoice;
    if (vendor_obj) vendor_name = vendor_obj.name;
    let restaurant_name = '';

    if (restaurants) {
      restaurants.forEach((restaurant) => {
        if (restaurant.id === invoice.restaurant) {
          restaurant_name = restaurant.name;
        }
      });
    }

    return (
      <View style={styles.header}>
        <View style={styles.headerItem}>
          <Text style={[styles.headerHeading, vendor_name ? {} : styles.missing]}>Vendor Name</Text>
          <View style={styles.headerVendorName}>
            <Text style={[styles.headerValue, styles.headerLeft, vendor_name ? {} : styles.missingValue]}>{vendor_name || 'Missing'}</Text>
            <View style={[styles.headerValue, styles.headerRight]}>
              {is_flagged
                ? (
                  <Image
                    resizeMode="contain"
                    source={Images.flag}
                    style={[styles.flag]}
                  />
                )
                : null}

              {is_vendor_supplied_invoice
                ? (
                  <Image
                    resizeMode="contain"
                    source={Images.mail_icon}
                    style={styles.email}
                  />
                )
                : null}
            </View>
          </View>
        </View>

        <View style={styles.headerItem}>
          <Text style={[styles.headerHeading, restaurant_name ? {} : styles.missing]}>Location Name</Text>
          <Text style={[styles.headerValue, restaurant_name ? {} : styles.missingValue]}>{restaurant_name || 'Missing'}</Text>
        </View>

        <View style={styles.lastHeaderItem}>
          <View style={styles.headerInvoiceNumber}>
            <Text style={[styles.headerHeading, invoice_number ? {} : styles.missing]}>Invoice Number</Text>
            <Text style={[styles.headerValue, invoice_number ? {} : styles.missingValue]}>{invoice_number || 'Missing'}</Text>
          </View>

          <View style={styles.headerInvoiceDate}>
            <Text style={[styles.headerHeading, styles.centerText, date ? {} : styles.missing]}>Invoice Date</Text>
            <Text style={[styles.headerValue, styles.centerText, date ? {} : styles.missingValue]}>{parserInvoiceDate(date) || 'Missing'}</Text>
          </View>

          <View style={styles.headerInvoiceTotal}>
            <Text style={[styles.headerHeading, styles.rightText]}>Total</Text>
            <Text style={[styles.headerValue, styles.rightText]}>
              {toCurrencyNoSpace(total_amount)}
            </Text>
          </View>
        </View>
      </View>
    );
  }

  renderFlagDialog() {
    const {
      isShowFlagDialog, showFlagAlert, flagText, setFlagText, invoice, addInvoiceFlag, resolveInvoiceFlag
    } = this.props;
    const { is_flagged } = invoice;
    const { filteredUsers } = this.state;

    return (
      <Modal
        hideModalContentWhileAnimating
        isVisible={isShowFlagDialog}
        backdropOpacity={0.5}
        onRequestClose={() => showFlagAlert(false)}
        onShow={() => {
          setFlagText('');
          // this.modalTextInput.focus();
        }}
      >
        <View style={styles.modalContainer}>
          <Text style={styles.modalHeading}>{is_flagged ? 'Resolve Invoice' : 'Flag Invoice'}</Text>
          <MentionsTextInput
            trigger="@"
            triggerLocation="anywhere"
            suggestionsPanelStyle={{ backgroundColor: 'rgba(100,100,100,0.1)' }}
            ref={(input) => { this.modalTextInput = input; }}
            textInputStyle={styles.modalInput}
            multiline
            textAlignVertical="top"
            minHeight={80}
            numberOfLines={4}
            placeholder={is_flagged ? 'Reason for Resolve (Required)' : 'Reason for Flag (Required)'}
            value={flagText}
            onChangeText={(text) => {
              setFlagText(text);
            }}
            suggestionsData={filteredUsers} // array of objects
            keyExtractor={(item) => item.name}
            triggerCallback={this.callback.bind(this)}
            suggestionRowHeight={45}
            horizontal={false}
            renderSuggestionsRow={this.renderSuggestionsRow.bind(this)}
            MaxVisibleRowCount={3}
          />
          <View style={styles.modalButtons}>
            <TouchableOpacity style={styles.modalButton} onPress={() => showFlagAlert(false)}>
              <Text style={[styles.modalButtonText, { color: Colors.red }]}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalButton}
              onPress={() => {
                if (flagText && flagText.length) {
                  const formattedText = this.getFlagText();
                  if (is_flagged) {
                    resolveInvoiceFlag(invoice.id, formattedText);
                    showFlagAlert(false);
                  } else {
                    addInvoiceFlag(invoice.id, formattedText);
                    showFlagAlert(false);
                  }
                }
              }}
            >
              <Text style={[styles.modalButtonText, flagText && flagText.length ? { color: Colors.deepSkyBlue } : { color: Colors.secondaryText }]}>Save</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    );
  }

  renderLoadingDialog() {
    const { isLoading } = this.props;
    return (
      <Spinner
        visible={isLoading}
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
      />
    );
  }

  renderTabs() {
    const { showInvoiceHistory, currentTab } = this.props;

    return (
      <ScrollableTabView
        style={{ marginTop: 10 }}
        initialPage={currentTab}
        renderTabBar={() => <DetailsTabBar />}
        onChangeTab={(index) => {
          this.onTabSelection(index);
        }}
      >
        {this.renderLineItems()}
        {this.renderGlSplits()}
        {this.renderImages()}
        {showInvoiceHistory ? this.renderHistory() : null}
      </ScrollableTabView>
    );
  }

  renderLineItems() {
    const {
      invoice
    } = this.props;
    const { has_manual_splits, is_ap_lite, has_line_items_loaded } = invoice;
    let { line_items } = invoice;
    if (!line_items) line_items = [];
    const hideItems = has_line_items_loaded && (has_manual_splits || is_ap_lite) && (line_items.length === 0);

    if (!has_line_items_loaded) {
      return (
        <View tabLabel="Items" style={styles.loading}>
          <ActivityIndicator
            size="small"
          />
        </View>
      );
    }
    if (!hideItems) {
      return (
        <View tabLabel="Items" style={styles.tabView}>
          <LineItems
            line_items={line_items}
          />
        </View>
      );
    }
    return null;
  }

  renderGlSplits() {
    const {
      invoice, expandGlSplits
    } = this.props;
    const { has_gl_splits_loaded } = invoice;
    let { gl_splits } = invoice;
    if (!gl_splits) gl_splits = [];

    if (!has_gl_splits_loaded) {
      return (
        <View tabLabel="GL Splits" style={styles.loading}>
          <ActivityIndicator
            size="small"
          />
        </View>
      );
    }

    return (
      <View tabLabel="GL Splits" style={styles.tabView}>
        <GlSplits
          expandGlSplits={expandGlSplits}
          gl_splits={gl_splits}
        />
      </View>
    );
  }

  renderImages() {
    const {
      invoice, goToInvoiceImage
    } = this.props;
    const { has_images_loaded } = invoice;
    let { images } = invoice;
    if (!images) images = [];

    if (!has_images_loaded) {
      return (
        <View tabLabel="Images" style={styles.loading}>
          <ActivityIndicator
            size="small"
          />
        </View>
      );
    }

    return (
      <View tabLabel="Images" style={styles.tabView}>
        <InvoiceImages
          images={images}
          onPress={goToInvoiceImage}
        />
      </View>
    );
  }

  renderHistory() {
    const {
      invoice
    } = this.props;
    const { has_history_loaded } = invoice;
    let { history } = invoice;
    if (!history) history = [];

    const items = history.map((item) => {
      const {
        reason, date, resolving
      } = item;
      let color = Colors.gray;
      if (reason) {
        if (reason.indexOf('info') !== -1 || reason.indexOf('info') !== -1) color = Colors.primary;
        else if (reason.indexOf('error') !== -1 || reason.indexOf('flagged') !== -1) color = Colors.danger;
        else if (reason.indexOf('paid') !== -1 || reason.indexOf('verified') !== -1 || reason.indexOf('finished') !== -1) color = Colors.success;
        else if (resolving) color = Colors.resolve;
      }

      return {
        date: parserInvoiceDate(date),
        time: parserInvoiceTime(date),
        title: title(this.getHistoryMessage(item)),
        description: this.getHistoryDescription(item),
        color
      };
    });

    if (!has_history_loaded) {
      return (
        <View tabLabel="History" style={styles.loading}>
          <ActivityIndicator
            size="small"
          />
        </View>
      );
    }

    return (
      <View tabLabel="History" style={styles.tabView}>
        <Timeline
          data={items}
          separator
          circleSize={12}
          lineWidth={0.5}
          options={{
            style: { paddingTop: 5 }
          }}
          timeContainerStyle={styles.timeContainerStyle}
        />
      </View>
    );
  }

  renderApproveButton() {
    const { approveInvoice, invoice } = this.props;
    const { links } = invoice;
    if (!links || !links.approve) {
      return null;
    }

    if (this.state.isApproved) {
      const sliderIcon = () => (
        <Icon
          name="check"
          style={styles.sliderSuccess}
        />
      );

      return (
        <View style={styles.approveButtonParent}>
          <SwipeButton
            disabled
            enableRightToLeftSwipe={this.state.isApproved}
            disabledRailBackgroundColor={Colors.primary}
            disabledThumbIconBackgroundColor={Colors.white}
            thumbIconBackgroundColor={Colors.white}
            thumbIconComponent={sliderIcon}
            title="Swipe to Approve"
            railBackgroundColor={Colors.primary}
            railFillBackgroundColor={Colors.primary}
            railBorderColor={Colors.primary}
            railFillBorderColor={Colors.primary}
            titleColor={Colors.white}
          />
        </View>
      );
    }

    const sliderIcon = () => (
      !invoice.isApproved ? <Image source={Images.plate_slider} style={styles.sliderButton} />
        : (
          <Icon
            name="check"
            style={styles.sliderSuccess}
          />
        )
    );

    return (
      <View style={styles.approveButtonParent}>
        <SwipeButton
          disabled={invoice.isApproved}
          disabledRailBackgroundColor={Colors.primary}
          disabledThumbIconBackgroundColor={Colors.white}
          thumbIconBackgroundColor={Colors.transparent}
          thumbIconComponent={sliderIcon}
          title="Swipe to Approve"
          onSwipeSuccess={() => approveInvoice(invoice.id)}
          railBackgroundColor={Colors.primary}
          railFillBackgroundColor={Colors.primary}
          railBorderColor={Colors.primary}
          railFillBorderColor={Colors.primary}
          titleColor={Colors.white}
        />
      </View>
    );
  }

  renderSuggestionsRow({ item }, hidePanel) {
    return (
      <TouchableOpacity onPress={() => this.onSuggestionTap(item, hidePanel)}>
        <View style={styles.suggestionsRowContainer}>
          <View style={styles.userIconBox}>
            <Text style={styles.usernameInitials}>{!!item.name && item.name.substring(0, 2).toUpperCase()}</Text>
          </View>
          <View style={styles.userDetailsBox}>
            <Text style={styles.displayNameText}>{item.name}</Text>
            <Text style={styles.usernameText}>
              @
              {item.name}
            </Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  }

  render() {
    const { invoice } = this.props;

    return (
      <View style={styles.container}>
        {invoice ? this.renderHeader() : null}
        {invoice ? this.renderTabs() : null}
        {invoice ? this.renderApproveButton() : null}
        {invoice ? this.renderFlagDialog() : null}
        {invoice ? this.renderLoadingDialog() : null}
      </View>
    );
  }
}

export default InvoiceDetail;
