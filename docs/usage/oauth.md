# OAuth Configuration
Starting with Beta 6, OSP includes a configuration option to add oAuth Sign-On using preconfigured and custom OAuth2 Servers, such as Discord, Reddit, Azure Active Directory, etc.

OSP OAuth configuration uses AuthLib (https://github.com/lepture/authlib).

## Adding an OAuth2 Provider
You can add a new provider from the Admin Screen->oAuth Providers, as seen below:

2020-05-05_06_40_27-osp_demo_-_administration_page.png

When adding a new provider, you will be required to enter configuration settings based on the provider. In the provider configuration below this section, we will compile a listing of know and working settings, but be aware not every service is the same. Most providers will require you to set up oAuth on their site, usually in a developer or application section.

## New oAuth Provider Settings Window
- Authentication Type: Select Preconfigured Providers or a Custom OAuth2 Configuration
- OAuth Provider ID: Shortname identifier for OSP to identify the OAuth Provider. This ID is used in URL shortcuts and can not have spaces.
- OAuth Provider Friendly Name: Display Name used on Login and Registration Pages to identify the service users will be logging in with.
- Login Button Color: Custom Color of the Login Button used on the Login and Registration Pages
- Client ID: Client ID or Application ID provided by the oAuth Provider
- Client Secret: Client Secret Key provided by the oAuth Provider
- Access Token URL: Access Token Retrieval endpoint for OAuth 2
- Access Token Params: Additional Parameters required for the Access Token Endpoint. Expressed as a JSON Value.
- Authorize URL: Endpoint for User Authorization of OAuth 2
- Authorize Token Params: Additional Parameters required for User Authorization. Expressed as a JSON Value.
- API Base URL: Full URI for API Requests to the Provider. (Ex: https://example.com/api/)
- Client Kwargs: Additional Arguments required to build an OAuth2 Session (https://docs.authlib.org/en/latest/client/api.html#authlib.integrations.requests_client.OAuth2Session). This is typically where you will place Authentication Scope such as:```{"scope":"email"}```
- Profile Endpoint: Path of API Base URL where User Profile information can be retrieved (Ex: me/@profile)
- ID Profile Value: Result Variable found in the results of a query to the Profile Endpoint which contains a unique ID value, typically "id"
- User Profile Value: Result Variable found in the results of a query to the Profile Endpoint which contains a username
- Email Profile Value: Result Variable found int the results of a query Profile Endpoint which contains an email address.
> Note: Not all services provide access to Email Addresses in their API. In this case, if OSP can not retrieve an email address, users will be prompted to add one when they log in.

## Additional Information
- Custom OAuth 2 services will not automatically download user photos to OSP. 
If you have a service that you have configured and would like automatic picture downloads, please open a feature request with your configuration settings and instructions on how to retrieve the pictures to be added into future OSP versions.
- Redirect URI Settings on OAuth2 Providers will be
```http(s)://<FQDN>/oauth/authorize/<oAuthProviderID>```
- Users who log in using an OAuth2 provider whose email address matches an existing local OSP account will be prompted to convert their local account into an oAuth account. During the process, the user will need to enter their local OSP account password to complete the process. Services which do not provide an email address in their user profile will not be able to convert local accounts at this time.
annotation_2020-05-05_073630.jpg

## Known OAuth Configurations
Coming Soon