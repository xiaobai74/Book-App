package com.novelmanager.app;

import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(android.os.Bundle savedInstanceState) {
        // 注册内联插件后再初始化 Bridge，JS 侧 registerPlugin('AppSettings') 即可调用
        registerPlugin(AppSettingsPlugin.class);
        super.onCreate(savedInstanceState);
    }

    // 返回键已由 @capacitor/app 插件派发至 JS 层（App.vue onHardwareBack），
    // 原生不再拦截 onBackPressed，避免覆盖 JS 监听。

    /**
     * 「所有文件访问」设置页跳转插件。
     *
     * Android 11+ 的 MANAGE_EXTERNAL_STORAGE 无法通过 requestPermissions() 弹窗授予
     * （Capacitor Filesystem 源码对 API≥30 直接返回 prompt 且系统不弹窗），只能引导
     * 用户到系统设置手动开启。Capacitor 8 的 Bridge.launchIntent 不解析 intent:// URI
     * （仅 ACTION_VIEW 包一层，ActivityNotFound 静默吞掉），故在原生侧显式 startActivity。
     *
     * 注意：必须是 public static 嵌套类——PluginHandle 用
     * getDeclaredConstructor().newInstance() 跨包反射实例化且不调 setAccessible，
     * 包私有类会抛 IllegalAccessException 导致插件静默加载失败。
     */
    @CapacitorPlugin(name = "AppSettings")
    public static class AppSettingsPlugin extends Plugin {

        /**
         * 真实的「所有文件访问」状态。
         * Capacitor Filesystem 插件在 Android 13+ 的 checkPermissions 恒返回 granted
         * （isStoragePermissionGranted 对 API≥33 直接 true），但公共目录直读仍需
         * MANAGE_EXTERNAL_STORAGE，JS 侧无法感知 → 扫描静默空结果。这里用
         * Environment.isExternalStorageManager() 暴露真实状态供 JS 判断。
         */
        @PluginMethod
        public void hasAllFilesAccess(PluginCall call) {
            boolean granted =
                Build.VERSION.SDK_INT < Build.VERSION_CODES.R || Environment.isExternalStorageManager();
            JSObject ret = new JSObject();
            ret.put("granted", granted);
            call.resolve(ret);
        }

        @PluginMethod
        public void openAllFilesAccessSettings(PluginCall call) {
            try {
                Intent intent;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    try {
                        // 直达本应用的「所有文件访问」开关页
                        intent = new Intent(
                            Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                            Uri.parse("package:" + getContext().getPackageName())
                        );
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        getContext().startActivity(intent);
                        call.resolve();
                        return;
                    } catch (ActivityNotFoundException ignored) {
                        // 个别 ROM 无应用级页面，回退到「所有文件访问」应用列表页
                    }
                }
                intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                intent.setData(Uri.parse("package:" + getContext().getPackageName()));
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(intent);
                call.resolve();
            } catch (ActivityNotFoundException e) {
                call.reject("无法打开系统设置页: " + e.getMessage());
            }
        }
    }
}
